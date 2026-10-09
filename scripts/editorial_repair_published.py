#!/usr/bin/env python3
"""Conservative, source-grounded repair of weak Ashdod descriptions.
Only updates already-published CMS overrides; no new publication or status changes.
"""
import json, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from enrich_event_content_ai import ask_model, clean_text, fetch_source_text, source_urls, sanitize_editorial_text

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview/ashdod/data/events.json"
AUDIT=ROOT/"events-preview/admin/data/content-quality-ashdod.json"
REPORT=ROOT/"events-preview/admin/data/editorial-repair-report-ashdod.json"
LIMIT=int(os.getenv("EDITORIAL_REPAIR_LIMIT","5"))
OFFSET=int(os.getenv("EDITORIAL_REPAIR_OFFSET","0"))
URL=os.getenv("SUPABASE_URL","").rstrip("/")
KEY=os.getenv("SUPABASE_SERVICE_ROLE_KEY","")
S=requests.Session()
S.headers.update({"apikey":KEY,"Content-Type":"application/json"})
if KEY.count(".")==2 and not KEY.startswith("sb_secret_"):
    S.headers["Authorization"]="Bearer "+KEY

def credible_specific(url,event):
    if not url or not url.startswith("https://"): return False
    parsed=urlparse(url)
    if parsed.hostname not in ("ashdod.smarticket.co.il","mishkan-ashdod.smarticket.co.il","live.tickchak.co.il","www.ofek-ashdod.org.il","ofek-ashdod.org.il"): return False
    # Directory and landing pages cannot ground event-specific assertions.
    return len(parsed.path.strip("/"))>=8 and (bool(parsed.query) or parsed.path.count("/")>=2)

def passes(result):
    q=result.get("editorial_questions") or {}
    supported=lambda k: isinstance(q.get(k),dict) and q[k].get("supported") is True and len(clean_text(q[k].get("answer")))>=12
    desc=sanitize_editorial_text(result.get("long_description"))
    pitch=sanitize_editorial_text(result.get("short_pitch"))
    return (result.get("content_ready_for_media") is True and supported("what") and supported("why_attend")
            and (supported("audience") or supported("participants"))
            and len(desc)>=140 and len(pitch)>=35 and len(pitch)<=350
            and not re.search(r'https?://|\\[מקור\\]',desc+" "+pitch))

def main():
    if not (URL and KEY and os.getenv("OPENAI_API_KEY")):
        raise SystemExit("Missing SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY or OPENAI_API_KEY")
    data={str(e.get("event_id")):e for e in json.loads(DATA.read_text()).get("events",[])}
    findings=json.loads(AUDIT.read_text()).get("events",[])
    rows=[]; updated=0; checked=0
    for finding in findings[OFFSET:]:
        if updated>=LIMIT or checked>=LIMIT*6: break
        if finding.get("severity")!="critical": continue
        event=data.get(str(finding.get("event_id")))
        if not event or event.get("content_locked") or str(event.get("start_date") or "")<datetime.now(timezone.utc).date().isoformat(): continue
        event_id=event.get("event_id")
        cms=S.get(URL+"/rest/v1/cms_event_records",params={"select":"*","city_slug":"eq.ashdod","event_id":"eq."+str(event_id)},timeout=25)
        cms.raise_for_status()
        records=cms.json()
        if not records or records[0].get("publication_status")!="published": continue
        row=records[0]
        if (row.get("payload") or {}).get("content_locked"): continue
        if (row.get("payload") or {}).get("editorial_repaired_at"): continue
        checked+=1
        links=[u for u in source_urls({**event,**(row.get("payload") or {})}) if credible_specific(u,event)]
        record={"event_id":event_id,"title":event.get("title"),"source_urls":links}
        if not links:
            record["status"]="skipped_no_specific_source";rows.append(record);continue
        source_url=links[0]; source=fetch_source_text(source_url)
        if len(source)<180:
            record["status"]="skipped_insufficient_primary_source";rows.append(record);continue
        try:
            result=ask_model(event,source,source_url,require_web_search=False)
            if not passes(result):
                record["status"]="rejected_editorial_gate";rows.append(record);continue
            desc=sanitize_editorial_text(result["long_description"])
            pitch=sanitize_editorial_text(result["short_pitch"])
            # Do not override with less substance or change editorial/manual content.
            payload=row.get("payload") or {}
            if payload.get("content_origin") in ("manual","editorial"):
                record["status"]="skipped_human_content";rows.append(record);continue
            # Update only copy fields. Do not touch image, time, ticketing, status or published_at.
            patched=dict(payload)
            patched.update({"long_description":desc,"short_pitch":pitch,
                            "editorial_questions":result["editorial_questions"],
                            "editorial_core_passed":True,
                            "editorial_answer_count":sum(bool((result["editorial_questions"].get(k) or {}).get("supported")) for k in ("what","audience","why_attend","participants")),
                            "editorial_review_status":"passed",
                            "content_enrichment_source":source_url,
                            "content_origin":"ai_enriched",
                            "editorial_repaired_at":datetime.now(timezone.utc).isoformat()})
            # Optimistic concurrency guard: don't overwrite content edited during generation.
            latest=S.get(URL+"/rest/v1/cms_event_records",params={"select":"updated_at,payload,publication_status","city_slug":"eq.ashdod","event_id":"eq."+str(event_id)},timeout=25)
            latest.raise_for_status()
            cur=latest.json()
            if not cur or cur[0].get("updated_at")!=row.get("updated_at") or cur[0].get("publication_status")!="published":
                record["status"]="skipped_concurrent_edit";rows.append(record);continue
            resp=S.patch(URL+"/rest/v1/cms_event_records",params={"city_slug":"eq.ashdod","event_id":"eq."+str(event_id),"updated_at":"eq."+str(row.get("updated_at"))},headers={"Prefer":"return=representation"},json={"payload":patched,"updated_at":datetime.now(timezone.utc).isoformat()},timeout=25)
            resp.raise_for_status()
            if not resp.json():
                record["status"]="skipped_concurrent_edit";rows.append(record);continue
            updated+=1;record.update({"status":"updated_published_cms","before":clean_text(payload.get("long_description") or event.get("long_description"))[:1000],"after":desc,"short_pitch":pitch})
        except Exception as exc:
            record.update({"status":"error","error":str(exc)[:500]})
            if "credit_balance_exhausted" in str(exc) or "insufficient_quota" in str(exc):
                rows.append(record);break
        rows.append(record)
        time.sleep(0.4)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"checked":checked,"updated":updated,"offset":OFFSET,"results":rows},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"checked":checked,"updated":updated,"statuses":[x["status"] for x in rows]},ensure_ascii=False))
if __name__=="__main__": main()

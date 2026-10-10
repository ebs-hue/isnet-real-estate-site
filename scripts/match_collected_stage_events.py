#!/usr/bin/env python3
"""Match collected stage performances to existing Ashdod events. Read-only.
No edits to CMS, editorial content, videos or images.
"""
import json,re
from difflib import SequenceMatcher
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]/"events-preview/admin/data"
def load(name):return json.loads((ROOT/name).read_text(encoding="utf-8"))
def norm(s):
    s=re.sub(r"[^\u0590-\u05ffA-Za-z0-9 ]"," ",str(s or "").casefold())
    return " ".join(s.split())
def bad_description(s):
    x=norm(s)
    return not x or "מחפשים הופעות" in x or "באתר מבלים ריכזנו" in x or len(x)<40
def bad_image(url):
    return not url or any(x in url.lower() for x in ("big_star.png","logo","placeholder","default-image","no-image"))
def main():
    a=load("unified-stage-events-ashdod-rishon.json")["events"]
    b=[x for x in load("event-enrichment-candidates-ashdod.json")["events"] if x.get("category") in {"music","standup","kids","theatre"}]
    candidates=[];used=set()
    for e in b:
        matches=[]
        for x in a:
            if x.get("city")!="ashdod":continue
            n1=norm(e.get("title"));n2=norm(x.get("title"))
            if not n1 or not n2:continue
            sim=SequenceMatcher(None,n1,n2).ratio()
            if n1!=n2 and sim<.88:continue
            if not x.get("date_time") or not x.get("venue"):continue
            # Original event IDs frequently encode YYYYMMDD; use only as corroboration.
            date=x["date_time"][:10].replace("-","")
            event_id=str(e.get("event_id") or "")
            date_verified=date in event_id
            matches.append({"source_id":x["source_id"],"source_url":x["source_url"],"title":x["title"],
               "score":round(sim,3),"same_date_in_existing_id":date_verified,
               "image_candidate_url":None if bad_image(x.get("image_url")) else x["image_url"],
               "description_candidate":None if bad_description(x.get("description")) else x["description"],
               "video_candidate_url":x.get("video_url") if not x.get("video_candidate_needs_review") else None})
        if matches:
            matches.sort(key=lambda x:(x["same_date_in_existing_id"],x["score"]),reverse=True)
            best=matches[0]
            candidates.append({"event_id":e["event_id"],"title":e["title"],"existing_category":e["category"],
               "existing_subcategory":e.get("subcategory"),"match_status":"strong_candidate" if best["same_date_in_existing_id"] and best["score"]>=.95 else "manual_occurrence_review",
               "matches":matches[:6],"needs_existing_cms_readback":True})
    out={"generated_at":datetime.now(timezone.utc).isoformat(),"scope":"ashdod_stage_only",
      "stage_events_evaluated":len(b),"events_with_title_and_date_candidates":len(candidates),
      "strong_candidates":sum(x["match_status"]=="strong_candidate" for x in candidates),
      "public_feed_modified":False,"cms_modified":False,
      "warning":"Do not auto-write: title/date matching needs venue and occurrence readback; reject generic descriptions and image placeholders.",
      "events":candidates}
    (ROOT/"stage-existing-match-audit-ashdod.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("stage_events_evaluated","events_with_title_and_date_candidates","strong_candidates")}))
if __name__=="__main__":main()

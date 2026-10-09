#!/usr/bin/env python3
"""Read-only editorial rewrite pilot. Never edits or publishes event records."""
import json
from datetime import datetime, timezone
from pathlib import Path
from enrich_event_content_ai import ask_model, clean_text, fetch_source_text, source_urls

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "events-preview/ashdod/data/events.json"
OUT = ROOT / "events-preview/admin/data/editorial-rewrite-pilot-ashdod.json"
TARGETS = ("נאמן למקור", "MALEVO", "אבנר גדסי")

def main():
    events = json.loads(SOURCE.read_text(encoding="utf-8")).get("events", [])
    results = []
    for title in TARGETS:
        matches = [e for e in events if title in clean_text(e.get("title"))]
        for event in matches[:2]:
            urls = source_urls(event)
            original = clean_text(event.get("long_description") or event.get("description") or event.get("short_pitch"))
            source_text = clean_text(event.get("source_detail_text"))
            used_url = ""
            for url in urls:
                fetched = fetch_source_text(url)
                if len(fetched) > len(source_text):
                    source_text, used_url = fetched, url
                if len(source_text) >= 180:
                    break
            row = {"event_id": event.get("event_id"), "title": event.get("title"),
                   "original_text": original, "source_urls_checked": urls,
                   "source_url_used": used_url, "source_text_length": len(source_text)}
            try:
                result = ask_model(event, source_text, used_url or (urls[0] if urls else ""), require_web_search=len(source_text)<180)
                questions = result.get("editorial_questions") or {}
                required = ("what", "why_attend")
                mandatory = all(isinstance(questions.get(k),dict) and questions[k].get("supported") is True and clean_text(questions[k].get("answer")) for k in required)
                count = sum(isinstance(questions.get(k),dict) and questions[k].get("supported") is True and clean_text(questions[k].get("answer")) != "" for k in ("what","audience","why_attend","participants"))
                row.update({"editorial_questions":questions,"supported_count":count,"mandatory_passed":bool(mandatory),
                            "suggested_short_pitch":result.get("short_pitch"),"suggested_long_description":result.get("long_description"),
                            "participants":result.get("participants"),"target_audience":result.get("target_audience"),
                            "missing_information":result.get("missing_information"),"suggestion_ready_for_review":bool(mandatory and count>=3),
                            "editorial_status":"draft_only_needs_human_approval"})
            except Exception as exc:
                row.update({"editorial_status":"model_error","error":str(exc)[:400]})
            results.append(row)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"mode":"read_only","results":results},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"tested":len(results),"drafts":sum(bool(x.get("suggested_long_description")) for x in results),"report":str(OUT)},ensure_ascii=False))
if __name__=="__main__":
    main()

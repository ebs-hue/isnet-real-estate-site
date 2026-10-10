#!/usr/bin/env python3
"""Read-only expired occurrence audit. No CMS or public feed mutation.

Delete only after expiry is independently verified and ingestion has been made
incapable of reintroducing removed occurrences. Today's occurrences stay.
"""
import json,os,re
from datetime import datetime,date
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"events-preview/ashdod/data/events.json"
OUT=ROOT/"events-preview/admin/data/expired-occurrences-audit-ashdod.json"

def valid_date(value):
    if not isinstance(value,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):return None
    try:return date.fromisoformat(value)
    except ValueError:return None

def main():
    payload=json.loads(FEED.read_text(encoding="utf-8"))
    events=payload.get("events",[])
    today=datetime.now(ZoneInfo("Asia/Jerusalem")).date()
    expired=[];retained=[];review=[]
    for e in events:
        start=valid_date(e.get("start_date"))
        end=valid_date(e.get("end_date"))
        identifier=e.get("event_id") or e.get("id")
        if not start:
            review.append({"event_id":identifier,"reason":"missing_or_invalid_start_date"});continue
        if end and end<start:
            review.append({"event_id":identifier,"reason":"end_precedes_start"});continue
        last=end or start
        if last<today:
            expired.append({"event_id":identifier,"start_date":str(start),"end_date":str(end) if end else None})
        else:
            retained.append(identifier)
    report={"generated_at":datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(),
            "cutoff_local_date":str(today),"timezone":"Asia/Jerusalem",
            "mode":"read_only","database_modified":False,"public_feed_modified":False,
            "count_total":len(events),"count_expired_candidates":len(expired),
            "count_retained":len(retained),"count_requires_review":len(review),
            "expired_occurrences":expired,"requires_review":review}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Expired occurrence candidates:",len(expired),"review:",len(review))

if __name__=="__main__":main()

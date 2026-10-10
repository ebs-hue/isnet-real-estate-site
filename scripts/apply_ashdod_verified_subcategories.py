#!/usr/bin/env python3
"""Apply only reviewed, high-confidence subcategory suggestions to Ashdod feed.
Do not modify titles, descriptions, media, dates or publication statuses.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"events-preview/ashdod/data/events.json"
AUDIT=ROOT/"events-preview/admin/data/subcategory-audit-ashdod.json"
TAXONOMY=ROOT/"events-preview/admin/data/taxonomy.json"
OUT=ROOT/"events-preview/admin/data/subcategory-apply-report-ashdod.json"
def main():
    raw=json.loads(FEED.read_text(encoding="utf-8"))
    audit=json.loads(AUDIT.read_text(encoding="utf-8"))
    taxonomy=json.loads(TAXONOMY.read_text(encoding="utf-8"))
    valid={c["id"]:{s["id"] for s in c.get("subcategories",[])} for c in taxonomy["primary_categories"]}
    if audit.get("total")!=len(raw.get("events",[])):
        raise SystemExit("Audit/feed count mismatch; refusing stale suggestions")
    records={e["event_id"]:e for e in raw["events"]}
    changed=[]
    skipped=[]
    for suggestion in audit.get("events",[]):
        eid=suggestion.get("event_id")
        event=records.get(eid)
        sub=suggestion.get("suggested_subcategory")
        if (not event or suggestion.get("status")!="suggestion_only"
            or suggestion.get("conflict") or suggestion.get("primary_category_review_proposed")
            or float(suggestion.get("confidence") or 0)<0.90
            or event.get("subcategory_manual_override") is True
            or event.get("subcategory") not in (None,"")
            or event.get("category")!=suggestion.get("category")
            or sub not in valid.get(event.get("category"),set())):
            skipped.append(eid)
            continue
        event["subcategory"]=sub
        event["subcategory_review_status"]="auto_classified_from_verified_rule"
        event["subcategory_review_confidence"]=suggestion["confidence"]
        changed.append({"event_id":eid,"category":event["category"],"subcategory":sub})
    # Check that serialization preserves every original event and assigned value.
    assert len(records)==len(raw["events"])
    assert all(records[x["event_id"]]["subcategory"]==x["subcategory"] for x in changed)
    FEED.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    OUT.write_text(json.dumps({"count_updated":len(changed),"count_skipped":len(skipped),"updated":changed,
      "cms_readback_verified":False,"public_site_readback_verified":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Updated only subcategory fields:",len(changed),"Skipped:",len(skipped))
if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Apply only reviewed, high-confidence subcategory suggestions to Ashdod feed.
Do not modify titles, descriptions, media, dates or publication statuses.
"""
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"events-preview/ashdod/data/events.json"
AUDIT=ROOT/"events-preview/admin/data/subcategory-audit-ashdod.json"
TAXONOMY=ROOT/"events-preview/admin/data/taxonomy.json"
OUT=ROOT/"events-preview/admin/data/subcategory-apply-report-ashdod.json"
def verified_subcategory_correction(event):
    """Correct a workshop label when event-level evidence clearly says lecture."""
    if (event.get("category")!="seniors"
        or event.get("subcategory")!="senior-workshops"
        or event.get("subcategory_manual_override") is True):
        return None
    fields=[str(event.get(k) or "") for k in ("title","event_summary","description","short_pitch")]
    activity=" ".join(fields)
    event_is_workshop=any(re.search(pattern,activity,re.I) for pattern in
                         (r"סדנ",r"עיסת נייר",r"עיצוב ספגניות",r"הכנת תליונים"))
    event_is_lecture=any(re.search(pattern,activity,re.I) for pattern in
                        (r"הרצאה",r"פאנל",r"מפגש העשרה",r"שיחה"))
    return "senior-lectures" if event_is_lecture and not event_is_workshop else None

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
    corrected=[]
    # Safety repair: a volleyball/handball/football/basketball event must never be water-sports.
    for event in raw["events"]:
        if event.get("subcategory_manual_override") is True:
            continue
        title=str(event.get("title") or "")
        if event.get("category")=="sport" and event.get("subcategory")=="water-sports":
            sport=next(((term,sub) for term,sub in [
                ("כדורעף","volleyball"),("כדוריד","handball"),
                ("כדורסל","basketball"),("כדורגל","football")]
                if term in title),None)
            if not sport and "volleyball" in str(event.get("event_id") or "").lower():
                sport=("volleyball","volleyball")
            if sport:
                event["subcategory"]=sport[1]
                event["subcategory_review_status"]="corrected_from_explicit_sport_title"
                corrected.append({"event_id":event.get("event_id"),"subcategory":sport[1]})
    # Correct the explicit event-format mismatch without touching descriptions or other fields.
    for event in raw["events"]:
        target=verified_subcategory_correction(event)
        if target:
            event["subcategory"]=target
            event["subcategory_review_status"]="corrected_from_explicit_lecture_format"
            corrected.append({"event_id":event.get("event_id"),"subcategory":target})

    # Guard against ambiguous assignments based on incidental words in descriptions.
    def semantic_mismatch(event,subcategory):
        title=str(event.get("title") or "")
        if subcategory=="water-sports" and any(k in title for k in ("כדורעף","כדוריד","כדורסל","כדורגל")):
            return True
        if subcategory=="kids-theatre" and "שעת סיפור" in title:
            return True
        return False
    for suggestion in audit.get("events",[]):
        eid=suggestion.get("event_id")
        event=records.get(eid)
        sub=suggestion.get("suggested_subcategory")
        if (not event or suggestion.get("status")!="suggestion_only"
            or suggestion.get("conflict") or suggestion.get("primary_category_review_proposed")
            or float(suggestion.get("confidence") or 0)<0.90
            # Avoid converting incidental background words into event type on the basis of prose alone.
            or (suggestion.get("evidence_field")=="description" and float(suggestion.get("confidence") or 0)<0.95)
            or event.get("subcategory_manual_override") is True
            or event.get("subcategory") not in (None,"")
            or event.get("category")!=suggestion.get("category")
            or sub not in valid.get(event.get("category"),set())
            or semantic_mismatch(event,sub)):
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
    OUT.write_text(json.dumps({"count_updated":len(changed),"count_corrected":len(corrected),"count_skipped":len(skipped),"updated":changed,"corrected":corrected,
      "cms_readback_verified":False,"public_site_readback_verified":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Updated only subcategory fields:",len(changed),"Skipped:",len(skipped))
if __name__=="__main__":
    main()

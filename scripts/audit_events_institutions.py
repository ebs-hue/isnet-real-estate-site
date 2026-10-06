#!/usr/bin/env python3
"""Daily, explainable coverage audit for ISNET event metadata.
This is an operational report only; it does not fabricate descriptions,
photographs, venue locations or contact details.
"""
import collections
import json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/"events-preview"
report={"generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cities":{},"notes":["איורי המחשה אינם תמונות מקוריות של אירועים",
                              "כתובת מפעיל אינה בהכרח כתובת הפעילות או נקודת היציאה לטיול"]}
for slug in ("ashdod","rishon-lezion"):
    data=json.loads((ROOT/slug/"data/events.json").read_text(encoding="utf-8"))
    r=json.loads((ROOT/slug/"data/institutions.json").read_text(encoding="utf-8"))
    events=data.get("events") or []
    photos=[e for e in events if e.get("image_verified") is True and e.get("image_publishable") is True]
    lectures=[e for e in events if e.get("category")=="lecture"]
    missing_venue=[e for e in events if not e.get("venue_institution_id")]
    unknown_venue=collections.Counter(e.get("venue") or "לא צוין" for e in missing_venue
          if e.get("venue") not in (data.get("city"),None,""))
    operators=collections.Counter(e.get("operator_id") for e in events if e.get("operator_id"))
    report["cities"][slug]={
        "city":data.get("city"),
        "total_events":len(events),
        "institution_count":len(r.get("institutions") or []),
        "venue_matched":sum(bool(e.get("venue_institution_id")) for e in events),
        "operator_matched":sum(bool(e.get("operator_id")) for e in events),
        "events_with_contact_phone":sum(bool(e.get("contact_phone") or e.get("purchase_phone")) for e in events),
        "events_with_specific_address":sum(bool(e.get("address")) for e in events),
        "official_photos_verified":len(photos),
        "lecture_total":len(lectures),
        "lectures_without_verified_event_photo":len(lectures)-sum(e in photos for e in lectures),
        "operator_event_counts":dict(operators),
        "frequently_unmatched_venue_names":[{"name":name,"count":count}
                                            for name,count in unknown_venue.most_common(15)]
    }
path=ROOT/"institution-quality-report.json"
path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
for city,s in report["cities"].items():
    print("QUALITY",city,"events:",s["total_events"],
          "venues matched:",s["venue_matched"],"contacts:",s["events_with_contact_phone"],
          "lecture photos pending:",s["lectures_without_verified_event_photo"],flush=True)

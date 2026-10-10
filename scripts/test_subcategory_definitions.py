#!/usr/bin/env python3
"""Fail fast if a subcategory has no definition or rules drift from canonical IDs."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/"events-preview/admin/data"
taxonomy=json.loads((root/"taxonomy.json").read_text(encoding="utf-8"))
definitions=json.loads((root/"subcategory-definitions.json").read_text(encoding="utf-8"))["categories"]
for category in taxonomy["primary_categories"]:
    cid=category["id"]
    assert cid in definitions, f"Missing primary category: {cid}"
    known={s["id"] for s in category["subcategories"]}
    defined=set(definitions[cid]["subcategories"])
    assert known==defined, f"Definition mismatch: {cid}: {known^defined}"
    for sid in known:
        meta=definitions[cid]["subcategories"][sid]
        assert meta.get("definition") and meta.get("positive_evidence"), f"Missing evidence: {cid}/{sid}"
from audit_ashdod_subcategories import infer, PRIMARY_REVIEW
valid={g["id"]:{s["id"] for s in g.get("subcategories",[])} for g in taxonomy["primary_categories"]}
samples=[
    ({"category":"seniors","title":"הזקן והים","description":"סיור חיצוני מודרך של קתדרת אופק"}, "senior-trips"),
    ({"category":"seniors","title":"פאנל עולם של אסתטיקה","description":"פאנל מקצועי על אסתטיקה"}, "senior-lectures"),
    ({"category":"seniors","title":"יונתן גת מונארט 2026","event_summary":"הרצאה של יונתן גת","long_description":"מנחה סדנאות והרצאות"}, "senior-lectures"),
    ({"category":"seniors","title":"עיסת נייר דלעת","description":"סדנת יצירה"}, "senior-workshops"),
    ({"category":"seniors","title":"ספורט על כיסא","description":"שיעור תנועה וכוח"}, "senior-sport"),
    ({"category":"seniors","title":"כח המילים והשפעותיהם","description":"שיחה על השפעתן של מילים"}, "senior-lectures"),
]
for event,expected in samples:
    candidate,confidence,evidence,conflict=infer(event,valid,definitions)
    assert candidate==expected and confidence>=0.95 and not conflict, (event, candidate, confidence, evidence, conflict)
assert not any(current=="seniors" and suggested=="community" for current,_,suggested in PRIMARY_REVIEW)
print("PASS: taxonomy coverage and explicit senior activity-format rules")

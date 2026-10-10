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
print("PASS: all current taxonomy subcategories have definitions and evidence")

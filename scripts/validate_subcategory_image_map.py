#!/usr/bin/env python3
"""Validate the event-image agent's image bank map against canonical subcategories."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
data=root/"events-preview/admin/data"
taxonomy=json.loads((data/"taxonomy.json").read_text(encoding="utf-8"))
definitions=json.loads((data/"subcategory-definitions.json").read_text(encoding="utf-8"))["categories"]
bank=json.loads((data/"subcategory-image-map.json").read_text(encoding="utf-8"))["categories"]
canonical={x["id"]:x for x in taxonomy["primary_categories"]}
assert set(bank)==set(canonical), "Image-bank primary categories drift from taxonomy"
count=0
registered=0
for cid,c in canonical.items():
    group=bank[cid]
    assert group["category_label"]==c["label"], f"Primary label mismatch: {cid}"
    subs={s["id"]:s for s in c["subcategories"]}
    assert set(group["subcategories"])==set(subs), f"Subcategory IDs mismatch: {cid}"
    for sid,s in subs.items():
        entry=group["subcategories"][sid]
        assert entry["subcategory_label"]==s["label"], f"Subcategory label mismatch: {cid}/{sid}"
        assert entry["meaning"]==definitions[cid]["subcategories"][sid]["definition"], f"Definition mismatch: {cid}/{sid}"
        image_files=entry["image_files"]
        assert isinstance(image_files,list), f"Missing image list {cid}/{sid}"
        assert len(image_files)==len(set(image_files)),f"Repeated image filename: {cid}/{sid}"
        for filename in image_files:
            assert isinstance(filename,str) and filename.strip(),f"Blank filename: {cid}/{sid}"
            assert not filename.startswith("http"),f"Image bank must use registered filenames, not remote URLs: {cid}/{sid}"
        registered+=len(image_files)
        count+=1
print(f"VALID: {count} subcategories aligned with taxonomy; {registered} registered subtype image references")

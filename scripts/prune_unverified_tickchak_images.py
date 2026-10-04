#!/usr/bin/env python3
import json
from pathlib import Path
from urllib.parse import urlsplit

root=Path(__file__).resolve().parents[1]
path=root/"events-preview"/"ashdod"/"data"/"events.json"
data=json.loads(path.read_text(encoding="utf-8"))

trusted_tickchak={
"evt_35_20261005","evt_36_20261006","evt_37_20261006","evt_38_20261008",
"evt_43_20261015","evt_46_20261020","evt_47_20261022","evt_50_20261024",
"evt_52_20261028","evt_57_20261105","evt_58_20261112","evt_59_20261121",
"evt_62_20261203","evt_63_20261205","evt_65_20261212","evt_67_20270102"
}

cleared=0
for e in data.get("events",[]):
    origin=e.get("image_origin_url") or ""
    host=(urlsplit(origin).hostname or "").lower()
    if host=="static.tickchak.co.il" and e.get("event_id") not in trusted_tickchak:
        e["image_url"]=None
        e["image_origin_url"]=None
        e["image_source"]=None
        e["image_credit"]=None
        e["image_publishable"]=False
        cleared+=1

path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"cleared_unverified_tickchak={cleared}")

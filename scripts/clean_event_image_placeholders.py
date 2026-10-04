#!/usr/bin/env python3
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
path=root/"events-preview"/"ashdod"/"data"/"events.json"
data=json.loads(path.read_text(encoding="utf-8"))
bad=(
    "/languages/il.gif",
    "artistshadow",
    "/images/live/more/eventnew.jpg",
    "eventnew.jpg",
    "no_pic",
    "no-pic",
    "placeholder",
    "smarticket_logo",
    "_logo_",
)
cleared=0
for event in data.get("events",[]):
    url=(event.get("image_url") or "").lower()
    if url and any(x in url for x in bad):
        event["image_url"]=None
        event["image_source"]=None
        event["image_credit"]=None
        event["image_publishable"]=False
        cleared+=1
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"cleared={cleared}")

#!/usr/bin/env python3
"""Build reusable artist/production profiles from the central media bank."""
from __future__ import annotations
import json, re, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BANK=ROOT/"events-preview"/"media-bank"/"data"/"media.json"
OUT=ROOT/"events-preview"/"media-bank"/"data"/"entities.json"

def norm(v):
    x=unicodedata.normalize("NFKC",str(v or "")).casefold()
    x=re.sub(r"[\u0591-\u05c7]","",x)
    return re.sub(r"\s+"," ",re.sub(r"[^0-9a-zא-ת]+"," ",x)).strip()

def main():
    doc=json.loads(BANK.read_text(encoding="utf-8"))
    groups={"artist":{},"production":{}}
    for m in doc.get("media",[]):
        if m.get("status")!="approved" or not m.get("publishable"):
            continue
        for kind,field in (("artist","artists"),("production","productions")):
            for label in m.get(field) or []:
                key=norm(label)
                if not key: continue
                g=groups[kind].setdefault(key,{
                    "entity_type":kind,
                    "entity_key":key,
                    "label":label,
                    "media_ids":[],
                    "cities":[],
                    "categories":[],
                    "events":[],
                    "preferred_media_id":None,
                    "usage_count":0,
                })
                if m["media_id"] not in g["media_ids"]: g["media_ids"].append(m["media_id"])
                for city in m.get("cities") or []:
                    if city not in g["cities"]: g["cities"].append(city)
                for cat in m.get("categories") or []:
                    if cat not in g["categories"]: g["categories"].append(cat)
                known={(x.get("city"),x.get("event_id")) for x in g["events"]}
                for ev in m.get("events") or []:
                    k=(ev.get("city"),ev.get("event_id"))
                    if k not in known:
                        g["events"].append(ev);known.add(k)
                # Prefer a non-AI, reusable, frequently used real source image.
                if not g["preferred_media_id"] and not m.get("ai_generated"):
                    g["preferred_media_id"]=m["media_id"]
                g["usage_count"]=len(g["events"])
    artists=sorted(groups["artist"].values(),key=lambda x:(-x["usage_count"],x["label"]))
    productions=sorted(groups["production"].values(),key=lambda x:(-x["usage_count"],x["label"]))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({
        "artists":artists,
        "productions":productions,
        "stats":{"artists":len(artists),"productions":len(productions)}
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"artists":len(artists),"productions":len(productions)},ensure_ascii=False))

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Point event-card thumbnails at lightweight central media-bank variants.

Full event images remain unchanged for detail pages. Only thumbnail_url is
replaced, so event cards load a small reusable WebP asset.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"events-preview"
BANK=BASE/"media-bank"/"data"/"media.json"
CITIES=["ashdod","rishon-lezion"]

def image_key(e):
    origin=e.get("image_origin_url") or ""
    url=e.get("image_url") or e.get("thumbnail_url") or ""
    seed=origin or url
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24] if seed else ""

def main():
    bank=json.loads(BANK.read_text(encoding="utf-8"))
    by_key={}
    for m in bank.get("media",[]):
        if m.get("status")!="approved" or m.get("publishable") is not True or not m.get("card_url"):
            continue
        mid=str(m.get("media_id") or "")
        key=mid.removeprefix("media_")
        if key:
            by_key[key]=m
    changed=0
    by_city={}
    for city in CITIES:
        p=BASE/city/"data"/"events.json"
        doc=json.loads(p.read_text(encoding="utf-8"))
        city_changed=0
        for e in doc.get("events",[]):
            if e.get("image_verified") is not True or e.get("image_publishable") is not True:
                continue
            m=by_key.get(image_key(e))
            if not m:
                continue
            thumb="/events-preview/"+str(m["card_url"]).lstrip("/")
            if e.get("thumbnail_url")==thumb and e.get("thumbnail_ready") is True:
                continue
            e["thumbnail_url"]=thumb
            e["thumbnail_ready"]=True
            e["thumbnail_source"]="central_media_bank_card"
            e["media_bank_id"]=m.get("media_id")
            city_changed+=1
        if city_changed:
            p.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        by_city[city]=city_changed
        changed+=city_changed
    print(json.dumps({"updated_thumbnails":changed,"by_city":by_city},ensure_ascii=False))

if __name__=="__main__":
    main()

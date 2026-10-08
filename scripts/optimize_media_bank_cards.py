#!/usr/bin/env python3
"""Create lightweight reusable card images for the ISNET central media bank."""
from __future__ import annotations

import hashlib, io, json, os, time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
BANK=ROOT/"events-preview"/"media-bank"/"data"/"media.json"
OUT=ROOT/"events-preview"/"media-bank"/"assets"/"cards"
MAX_W=960
MAX_H=720
TARGET_BYTES=170_000
UA={"User-Agent":"Mozilla/5.0 (compatible; ISNET-MediaBank/1.0)"}

def local_source(item):
    u=str(item.get("url") or "")
    if not u or u.startswith(("http://","https://","data:")):
        return None
    for city in item.get("cities") or []:
        p=ROOT/"events-preview"/city/u
        if p.is_file(): return p
    return None

def remote_source(item):
    for u in (item.get("origin_url"),item.get("url")):
        if isinstance(u,str) and u.startswith("https://"):
            return u
    return None

def load_bytes(item):
    p=local_source(item)
    if p:
        try:return p.read_bytes()
        except OSError:return None
    u=remote_source(item)
    if not u:return None
    try:
        r=requests.get(u,headers=UA,timeout=20,stream=True)
        r.raise_for_status()
        c=(r.headers.get("content-type") or "").lower()
        if not c.startswith("image/"):return None
        buf=bytearray()
        for chunk in r.iter_content(65536):
            buf.extend(chunk)
            if len(buf)>12_000_000:return None
        return bytes(buf)
    except requests.RequestException:
        return None

def encode(img):
    q=80
    while q>=58:
        b=io.BytesIO()
        img.save(b,"WEBP",quality=q,method=5)
        raw=b.getvalue()
        if len(raw)<=TARGET_BYTES or q==58:return raw,q
        q-=4

def main():
    doc=json.loads(BANK.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True,exist_ok=True)
    made=kept=failed=0
    total_bytes=0
    for item in doc.get("media",[]):
        if item.get("status")!="approved" or not item.get("publishable"):
            continue
        name=item["media_id"].replace("media_","")+".webp"
        dest=OUT/name
        if dest.is_file():
            raw=dest.read_bytes()
            item["card_url"]="media-bank/assets/cards/"+name
            item["card_bytes"]=len(raw)
            kept+=1;total_bytes+=len(raw)
            continue
        raw=load_bytes(item)
        if not raw:
            failed+=1;continue
        try:
            with Image.open(io.BytesIO(raw)) as im:
                im=ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((MAX_W,MAX_H),Image.Resampling.LANCZOS)
                payload,q=encode(im)
                dest.write_bytes(payload)
                item["card_url"]="media-bank/assets/cards/"+name
                item["card_width"]=im.width
                item["card_height"]=im.height
                item["card_bytes"]=len(payload)
                item["card_quality"]=q
                made+=1;total_bytes+=len(payload)
        except (OSError,ValueError):
            failed+=1
    doc["card_optimization"]={
        "generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "max_width":MAX_W,"max_height":MAX_H,"target_bytes":TARGET_BYTES,
        "generated":made,"reused":kept,"failed":failed,
        "total_card_bytes":total_bytes
    }
    BANK.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(doc["card_optimization"],ensure_ascii=False))

if __name__=="__main__":
    main()

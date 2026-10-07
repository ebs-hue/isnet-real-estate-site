#!/usr/bin/env python3
"""Create lightweight card variants for approved local media-bank images.

Only local repository images are processed. Originals remain untouched.
Outputs are deduplicated by file bytes and stored once under media-bank/cards.
"""
from __future__ import annotations
import hashlib, io, json
from pathlib import Path
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
EVENTS=ROOT/"events-preview"
BANK=EVENTS/"media-bank"/"data"/"media.json"
OUT=EVENTS/"media-bank"/"cards"
TARGET_W=900
QUALITY=80

def resolve_local(item):
    url=str(item.get("url") or "")
    if not url or url.startswith(("http://","https://","data:")):
        return None
    cities=item.get("cities") or []
    for city in cities:
        p=EVENTS/city/url
        if p.is_file():
            return p
    return None

def main():
    doc=json.loads(BANK.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True,exist_ok=True)
    made=reused=skipped=0
    for item in doc.get("media",[]):
        if item.get("status")!="approved" or not item.get("publishable"):
            continue
        src=resolve_local(item)
        if not src:
            skipped+=1
            continue
        raw=src.read_bytes()
        checksum=hashlib.sha256(raw).hexdigest()
        name=checksum[:24]+".webp"
        dest=OUT/name
        if not dest.exists():
            try:
                with Image.open(io.BytesIO(raw)) as im:
                    im=ImageOps.exif_transpose(im).convert("RGB")
                    w,h=im.size
                    if w>TARGET_W:
                        nh=max(1,round(h*TARGET_W/w))
                        im=im.resize((TARGET_W,nh),Image.Resampling.LANCZOS)
                    out=io.BytesIO()
                    im.save(out,"WEBP",quality=QUALITY,method=6)
                    dest.write_bytes(out.getvalue())
                    item["card_width"]=im.width
                    item["card_height"]=im.height
                    item["card_bytes"]=len(out.getvalue())
                    made+=1
            except Exception:
                skipped+=1
                continue
        else:
            reused+=1
            try:
                with Image.open(dest) as im:
                    item["card_width"],item["card_height"]=im.size
                item["card_bytes"]=dest.stat().st_size
            except Exception:
                pass
        item["card_url"]="media-bank/cards/"+name
        item["original_checksum"]=checksum
    doc.setdefault("optimization",{})
    doc["optimization"].update({
        "target_width":TARGET_W,
        "format":"webp",
        "quality":QUALITY,
        "created":made,
        "reused":reused,
        "skipped":skipped,
    })
    BANK.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(doc["optimization"],ensure_ascii=False))

if __name__=="__main__":
    main()

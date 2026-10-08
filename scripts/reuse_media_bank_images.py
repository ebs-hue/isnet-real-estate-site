#!/usr/bin/env python3
"""Reuse approved central media-bank images for matching future events.

Only exact normalized artist/production matches are reused. This prevents a
new city run from re-searching or regenerating media that the network already
approved for the same artist/show.
"""
from __future__ import annotations
import argparse, json, re, unicodedata
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"events-preview"
BANK=BASE/"media-bank"/"data"/"media.json"
ARTISTS=BASE/"media-bank"/"data"/"artists.json"\nPRODUCTIONS=BASE/"media-bank"/"data"/"productions.json"

def norm(v):
    x=unicodedata.normalize("NFKC",str(v or "")).casefold()
    x=re.sub(r"[\u0591-\u05c7]","",x)
    return re.sub(r"\s+"," ",re.sub(r"[^0-9a-zא-ת]+"," ",x)).strip()

def event_entities(e):
    artists=[]
    for key in ("artist_name","performer","speaker"):
        v=e.get(key)
        if isinstance(v,str) and v.strip(): artists.append(v.strip())
    p=e.get("participants") or []
    if isinstance(p,list): artists += [str(x).strip() for x in p if str(x).strip()]
    elif isinstance(p,str) and p.strip(): artists.append(p.strip())
    productions=[x for x in (e.get("production_name"),e.get("series_name"),e.get("title")) if isinstance(x,str) and x.strip()]
    return [norm(x) for x in artists if norm(x)],[norm(x) for x in productions if norm(x)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--city",required=True,choices=["ashdod","rishon-lezion"])
    args=ap.parse_args()
    data_path=BASE/args.city/"data"/"events.json"
    if not BANK.is_file() or not ARTISTS.is_file() or not PRODUCTIONS.is_file():
        print("media bank not ready"); return 0
    bank=json.loads(BANK.read_text(encoding="utf-8"))
    artist_doc=json.loads(ARTISTS.read_text(encoding="utf-8"))
    production_doc=json.loads(PRODUCTIONS.read_text(encoding="utf-8"))
    media={m["media_id"]:m for m in bank.get("media",[]) if m.get("status")=="approved" and m.get("publishable")}
    lookup={"artist":{},"production":{}}
    for e in artist_doc.get("artists",[]):
        mid=e.get("preferred_media_id")
        if mid in media: lookup["artist"][e.get("artist_key") or norm(e.get("name"))]=mid
    for e in production_doc.get("productions",[]):
        mid=e.get("preferred_media_id")
        if mid in media: lookup["production"][e.get("production_key") or norm(e.get("name"))]=mid

    doc=json.loads(data_path.read_text(encoding="utf-8"))
    reused=0
    today=date.today().isoformat()
    for e in doc.get("events",[]):
        if str(e.get("start_date") or "")<today: continue
        if e.get("image_verified") is True and e.get("image_publishable") is True:
            continue
        artists,productions=event_entities(e)
        mid=None; matched_type=None; matched_key=None
        for k in artists:
            if k in lookup["artist"]:
                mid=lookup["artist"][k];matched_type="artist";matched_key=k;break
        if not mid:
            for k in productions:
                if k in lookup["production"]:
                    mid=lookup["production"][k];matched_type="production";matched_key=k;break
        if not mid: continue
        m=media[mid]
        card=m.get("card_url")
        if card:
            url="/events-preview/"+card.lstrip("/")
        else:
            url=m.get("url")
            # Relative city-local assets are not portable across cities.
            if not isinstance(url,str) or (not url.startswith("https://") and not url.startswith("/events-preview/")):
                continue
        e.update({
            "image_url":url,
            "thumbnail_url":url,
            "image_source":m.get("source_url"),
            "image_origin_url":m.get("origin_url"),
            "image_credit":m.get("credit"),
            "image_rights_status":m.get("rights_status"),
            "image_verified":True,
            "image_publishable":True,
            "image_strategy":"central_media_bank_reuse",
            "media_bank_id":mid,
            "media_bank_match_type":matched_type,
            "media_bank_match_key":matched_key,
            "thumbnail_ready":True,
        })
        reused+=1
        print(f"REUSE {args.city}: {e.get('title')} <- {mid} ({matched_type})")
    if reused:
        data_path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"city":args.city,"reused":reused},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

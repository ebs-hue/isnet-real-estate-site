#!/usr/bin/env python3
"""Build the central ISNET media-bank index from city event datasets.

This first operational layer does not duplicate image binaries. It registers
each distinct image once and links it to every event/city/category/artist/show
that uses it. Local optimized event images remain referenced in place until
Storage migration is enabled.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
EVENTS=ROOT/"events-preview"
OUT=EVENTS/"media-bank"/"data"/"media.json"
CITIES={
    "ashdod": EVENTS/"ashdod"/"data"/"events.json",
    "rishon-lezion": EVENTS/"rishon-lezion"/"data"/"events.json",
}
BAD=("microsoft_oauth","google_oauth","facebook_oauth","oauth","placeholder","no-image","no_image","favicon","sprite","loading","pixel")

def norm(v):
    x=unicodedata.normalize("NFKC",str(v or "")).casefold()
    x=re.sub(r"[\u0591-\u05c7]","",x)
    return re.sub(r"\s+"," ",re.sub(r"[^0-9a-zא-ת]+"," ",x)).strip()

def is_bad(url):
    low=str(url or "").lower()
    return any(x in low for x in BAD)

def image_key(e):
    origin=e.get("image_origin_url") or ""
    url=e.get("thumbnail_url") or e.get("image_url") or ""
    seed=origin or url
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24] if seed else ""

def category_label(e):
    return e.get("category") or "other"

def people(e):
    out=[]
    for key in ("artist_name","performer","speaker"):
        v=e.get(key)
        if isinstance(v,str) and v.strip(): out.append(v.strip())
    ps=e.get("participants") or []
    if isinstance(ps,list):
        out.extend(str(x).strip() for x in ps if str(x).strip())
    elif isinstance(ps,str) and ps.strip():
        out.append(ps.strip())
    seen=set(); result=[]
    for x in out:
        n=norm(x)
        if n and n not in seen:
            seen.add(n); result.append(x)
    return result

def main():
    assets={}
    links=defaultdict(list)
    now=datetime.now(timezone.utc).isoformat()
    stats={"events_scanned":0,"image_links":0,"unique_images":0,"approved":0,"needs_review":0,"rejected":0}
    for city,path in CITIES.items():
        doc=json.loads(path.read_text(encoding="utf-8"))
        for e in doc.get("events",[]):
            if str(e.get("start_date") or "") < datetime.now().date().isoformat():
                continue
            stats["events_scanned"]+=1
            raw=e.get("thumbnail_url") or e.get("image_url") or ""
            if not raw: continue
            key=image_key(e)
            if not key: continue
            rejected=is_bad(raw) or is_bad(e.get("image_origin_url"))
            approved=bool(e.get("image_verified") is True and e.get("image_publishable") is True and not rejected)
            status="approved" if approved else ("rejected" if rejected else "needs_review")
            if key not in assets:
                assets[key]={
                    "media_id":"media_"+key,
                    "url":raw,
                    "origin_url":e.get("image_origin_url"),
                    "source_url":e.get("image_source") or e.get("detail_source_url") or e.get("ticket_url"),
                    "credit":e.get("image_credit"),
                    "rights_status":e.get("image_rights_status") or "unknown",
                    "status":status,
                    "verified":bool(e.get("image_verified") is True),
                    "publishable":bool(e.get("image_publishable") is True and not rejected),
                    "ai_generated":bool(e.get("image_ai_generated") is True or e.get("image_strategy")=="ai_generated"),
                    "strategy":e.get("image_strategy"),
                    "artists":[],
                    "productions":[],
                    "categories":[],
                    "cities":[],
                    "events":[],
                    "usage_count":0,
                    "created_from":"event_dataset",
                }
            a=assets[key]
            if a["status"]!="rejected":
                a["status"]="approved" if approved else a["status"]
            vals={
                "artists": people(e),
                "productions":[x for x in [e.get("production_name"),e.get("series_name"),e.get("title")] if x],
                "categories":[category_label(e)],
                "cities":[city],
            }
            for field,xs in vals.items():
                known={norm(x) for x in a[field]}
                for x in xs:
                    if norm(x) not in known:
                        a[field].append(x);known.add(norm(x))
            ref={"city":city,"event_id":e.get("event_id"),"title":e.get("title"),"date":e.get("start_date")}
            if not any(x["city"]==city and x["event_id"]==ref["event_id"] for x in a["events"]):
                a["events"].append(ref)
            a["usage_count"]=len(a["events"])
            stats["image_links"]+=1

    rows=sorted(assets.values(),key=lambda x:(x["status"]!="approved",-x["usage_count"],x["media_id"]))
    for x in rows: stats[x["status"]]+=1
    stats["unique_images"]=len(rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"generated_at":now,"stats":stats,"media":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(stats,ensure_ascii=False))

if __name__=="__main__":
    main()

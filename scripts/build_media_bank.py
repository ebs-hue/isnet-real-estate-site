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
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
EVENTS=ROOT/"events-preview"
OUT=EVENTS/"media-bank"/"data"/"media.json"
ARTISTS_OUT=EVENTS/"media-bank"/"data"/"artists.json"
PRODUCTIONS_OUT=EVENTS/"media-bank"/"data"/"productions.json"
CITIES={
    "ashdod": EVENTS/"ashdod"/"data"/"events.json",
    "rishon-lezion": EVENTS/"rishon-lezion"/"data"/"events.json",
}
GENERIC_PEOPLE={"אבא","אמא","הורים","ילדים","ילדות","משפחה","משפחות","קהל","משתתפים","משתתפות","מרצה","מנחה","אמן","אמנית","זמר","זמרת","שחקן","שחקנית"}
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

def similarity(a,b):
    a,b=norm(a),norm(b)
    if not a or not b: return 0.0
    if a==b: return 1.0
    sa,sb=set(a.split()),set(b.split())
    token=(len(sa&sb)/max(1,len(sa|sb)))
    return .7*SequenceMatcher(None,a,b).ratio()+.3*token

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
        if not n or n in GENERIC_PEOPLE or n.startswith("אבא ") or n.startswith("אמא "):
            continue
        if n not in seen:
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

    # Detect suspicious image reuse across unrelated productions. Do not hard reject:
    # flag for media QA so a legitimate series/artist image can still be kept.
    for a in assets.values():
        titles=[x for x in a.get("productions",[]) if x]
        min_sim=1.0
        if len(titles)>1:
            for i in range(len(titles)):
                for j in range(i+1,len(titles)):
                    min_sim=min(min_sim,similarity(titles[i],titles[j]))
        a["reuse_risk"]="review" if len(titles)>1 and min_sim<0.24 else "low"
        a["reuse_similarity_floor"]=round(min_sim,3) if len(titles)>1 else None
        if a["reuse_risk"]=="review" and a["status"]=="approved":
            a["status"]="needs_review"
            a["publishable"]=False
            a["review_reason"]="same_image_used_for_dissimilar_event_titles"

    rows=sorted(assets.values(),key=lambda x:(x["status"]!="approved",-x["usage_count"],x["media_id"]))
    for x in rows: stats[x["status"]]+=1
    stats["unique_images"]=len(rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    payload={"generated_at":now,"stats":stats,"media":rows}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    # Reusable entity indexes. These are intentionally network-wide rather than city-owned.
    artist_map={}
    production_map={}
    for a in rows:
        for artist in a.get("artists",[]):
            key=norm(artist)
            ent=artist_map.setdefault(key,{"artist_key":key,"name":artist,"media":[],"cities":[],"categories":[]})
            ent["media"].append(a["media_id"])
            ent["cities"]=sorted(set(ent["cities"]+a.get("cities",[])))
            ent["categories"]=sorted(set(ent["categories"]+a.get("categories",[])))
        for production in a.get("productions",[]):
            key=norm(production)
            ent=production_map.setdefault(key,{"production_key":key,"name":production,"media":[],"cities":[],"categories":[]})
            ent["media"].append(a["media_id"])
            ent["cities"]=sorted(set(ent["cities"]+a.get("cities",[])))
            ent["categories"]=sorted(set(ent["categories"]+a.get("categories",[])))
    ARTISTS_OUT.write_text(json.dumps({"generated_at":now,"artists":sorted(artist_map.values(),key=lambda x:x["name"])},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    PRODUCTIONS_OUT.write_text(json.dumps({"generated_at":now,"productions":sorted(production_map.values(),key=lambda x:x["name"])},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(stats,ensure_ascii=False))

if __name__=="__main__":
    main()

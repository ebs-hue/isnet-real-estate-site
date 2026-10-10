#!/usr/bin/env python3
"""Read-only FRIENDS discovery for Ashdod and Rishon LeZion.

Outputs auditable source candidates. Does not publish, modify events or download images.
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"events-preview/admin/data/event-source-priority.json"
OUTPUT=ROOT/"events-preview/admin/data/friends-discovery.json"
UA="ISNET-Events-Source-Discovery/1.0 (contact via isnet.co.il)"
HEADERS={"User-Agent":UA,"Accept-Language":"he-IL,he;q=0.9"}
def clean(s):
    return re.sub(r"\\s+"," ",str(s or "")).strip()

def get(url, session):
    r=session.get(url,headers=HEADERS,timeout=25)
    r.raise_for_status()
    if urlparse(r.url).hostname not in {"friends-hist.co.il","www.friends-hist.co.il"}:
        raise ValueError("Unexpected redirect")
    return BeautifulSoup(r.text,"html.parser")

def extract_city(soup,city):
    found={}
    for a in soup.select('a[href*="/show/"]'):
        href=urljoin("https://friends-hist.co.il/",a.get("href","")).split("#")[0]
        if urlparse(href).hostname not in {"friends-hist.co.il","www.friends-hist.co.il"}:
            continue
        title=clean(a.get_text(" ",strip=True)) or clean(a.get("title"))
        if not title:
            img=a.find("img")
            title=clean(img.get("alt")) if img else ""
        if not title or title in {"לפרטים והזמנה","להזמנה","פרטים נוספים"}:
            continue
        found.setdefault(href,{"title":title,"production_url":href,"city":city,"source_id":"friends-hist",
                              "rights_status":"not_verified","status":"candidate_requires_event_date_validation"})
    return list(found.values())

def main():
    source=next(s for s in json.loads(CONFIG.read_text(encoding="utf-8"))["sources"] if s["id"]=="friends-hist")
    items=[]; errors=[]
    with requests.Session() as session:
        for entry in source["cities"]:
            try:
                page=get(entry["url"],session)
                matches=extract_city(page,entry["slug"])
                items.extend(matches)
            except Exception as exc:
                errors.append({"city":entry["slug"],"error":type(exc).__name__+": "+str(exc)[:240]})
            time.sleep(2)
    report={"generated_at":datetime.now(timezone.utc).isoformat(),"source_id":"friends-hist",
            "publication_enabled":False,"cms_updated":False,"image_reuse_authorized":False,
            "city_counts":{c["slug"]:sum(v["city"]==c["slug"] for v in items) for c in source["cities"]},
            "errors":errors,"candidates":items}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    print(json.dumps({"city_counts":report["city_counts"],"errors":errors},ensure_ascii=False))
if __name__=="__main__":
    main()

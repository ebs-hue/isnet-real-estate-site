#!/usr/bin/env python3
"""Read-only first-pass discovery from configured national event boards.
This is a candidate index, not an event ingest, category classifier or image license.
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
OUT=ROOT/"events-preview/admin/data/national-events-discovery.json"
CITIES={"ashdod":("אשדוד",),"rishon-lezion":("ראשון לציון","ראשל״צ","ראשל\u05f4צ")}
HEADERS={"User-Agent":"ISNET-Events-Research/1.0 (isnet.co.il)","Accept-Language":"he-IL,he;q=0.9"}
def clean(x):
    return re.sub(r"\s+"," ",str(x or "")).strip()
def main():
    sources=json.loads(CONFIG.read_text(encoding="utf-8"))["sources"]
    results=[];source_reports=[]
    session=requests.Session()
    for s in sources:
        if not s.get("enabled") or not s.get("homepage_url"):
            continue
        city_pages=[c for c in s.get("cities",[]) if c.get("slug")=="ashdod" and c.get("url")]
        url=city_pages[0]["url"] if city_pages else s["homepage_url"]
        city_page=bool(city_pages)
        found=[];error=None
        try:
            resp=session.get(url,headers=HEADERS,timeout=20)
            resp.raise_for_status()
            if (urlparse(resp.url).hostname or "").removeprefix("www.") != s["domain"].removeprefix("www."):
                raise ValueError("cross-domain redirect")
            soup=BeautifulSoup(resp.text,"html.parser")
            seen=set()
            for a in soup.find_all("a",href=True):
                title=clean(a.get_text(" ",strip=True))[:250]
                href=urljoin(resp.url,a["href"]).split("#")[0]
                host=urlparse(href).hostname or ""
                if host!=s["domain"] and not host.endswith("."+s["domain"]):
                    continue
                if not 9<=len(title)<=250 or href in seen:
                    continue
                context=clean(a.parent.get_text(" ",strip=True))[:350] if a.parent else title
                city=next((slug for slug,terms in CITIES.items() if any(term in title or term in context for term in terms)),None)
                # Ashdod-discovery requires actual city evidence or a city-specific page.
                # Generic nationwide candidates are useful for enrichment, not city event creation.
                if not city_page and city!="ashdod":
                    continue
                seen.add(href)
                image=a.find("img")
                candidate_image=urljoin(resp.url,image.get("src") or image.get("data-src") or "") if image else None
                found.append({"source_id":s["id"],"city_hint":"ashdod" if city_page else city,"source_url":href,
                              "city_evidence":"city_listing_url" if city_page else "card_text",
                              "title_candidate":title,"source_context":context,
                              "image_candidate_url":candidate_image if candidate_image and candidate_image.startswith("https://") else None,
                              "status":"candidate_requires_title_city_date_and_venue_validation",
                              "image_rights_status":"unknown"})
                if len(found)>=250:break
        except Exception as exc:
            error=type(exc).__name__+": "+str(exc)[:180]
        results.extend(found)
        source_reports.append({"source_id":s["id"],"found":len(found),"error":error})
        time.sleep(2)
    OUT.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),
      "publication_enabled":False,"images_authorized":False,"cms_modified":False,
      "source_reports":source_reports,"candidates":results},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(source_reports,ensure_ascii=False))
if __name__=="__main__":
    main()

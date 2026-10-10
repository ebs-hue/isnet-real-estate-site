#!/usr/bin/env python3
"""Single, read-only collector for stage performances in Ashdod and Rishon.
Collect from national ticket boards in one pass; specialists work only on gaps.
"""
import json, re, time, hashlib
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview/admin/data"
CFG=DATA/"event-source-priority.json"
OUT=DATA/"unified-stage-events-ashdod-rishon.json"
CITIES={"ashdod":("אשדוד",),"rishon-lezion":("ראשון לציון","ראשלצ","ראשל״צ")}
CATS={"music","standup","kids","theatre"}
HEAD={"User-Agent":"ISNET-Stage-Discovery/1.0 (isnet.co.il)","Accept-Language":"he-IL,he;q=0.9"}
GENERIC=("אירועים באשדוד","אירועים בראשון","כל האירועים","לוח אירועים","לאתר המכירה","הצג עוד")
def clean(x):return re.sub(r"\s+"," ",str(x or "")).strip()
def domain(url,hostname):
    host=(urlparse(url).hostname or "").removeprefix("www.")
    root=hostname.removeprefix("www.")
    return host==root or host.endswith("."+root)
def txtmeta(soup,k):
    el=soup.find("meta",attrs={"property":k}) or soup.find("meta",attrs={"name":k})
    return clean(el.get("content")) if el else None
def collect_jsonld(soup):
    result=[]
    for s in soup.select('script[type="application/ld+json"]'):
        try: data=json.loads(s.string or s.get_text())
        except (ValueError,TypeError):continue
        def walk(obj):
            if isinstance(obj,list):
                for v in obj:walk(v)
            elif isinstance(obj,dict):
                kind=obj.get("@type",[])
                if isinstance(kind,str):kind=[kind]
                if any("Event" in str(t) for t in kind):result.append(obj)
                for k in ("@graph","itemListElement"):walk(obj.get(k,[]))
        walk(data)
    return result
def event_from_jsonld(obj,source_id,page):
    location=obj.get("location") or {}
    if isinstance(location,list):location=location[0] if location else {}
    if isinstance(location,str):location={"name":location}
    address=location.get("address") or {}
    if isinstance(address,str):address={"streetAddress":address}
    city=clean(address.get("addressLocality"))
    loc=clean(location.get("name"))
    found_city=next((key for key,names in CITIES.items() if any(n in city or n in loc for n in names)),None)
    name=clean(obj.get("name"))
    if not found_city or not name:return None
    image=obj.get("image")
    if isinstance(image,list):image=image[0] if image else None
    if isinstance(image,dict):image=image.get("url") or image.get("contentUrl")
    offers=obj.get("offers") or {}
    if isinstance(offers,list):offers=offers[0] if offers else {}
    video=obj.get("video") or {}
    if isinstance(video,list):video=video[0] if video else {}
    if isinstance(video,dict):video=video.get("embedUrl") or video.get("contentUrl") or video.get("url")
    return {"title":name,"city":found_city,"venue":loc or None,"date_time":obj.get("startDate"),
      "end_time":obj.get("endDate"),"description":clean(obj.get("description")) or None,
      "image_url":urljoin(page,image) if isinstance(image,str) else None,
      "video_url":video if isinstance(video,str) else None,
      "tickets_url":offers.get("url") if isinstance(offers,dict) else None,
      "category":None,"subcategory":None,"source_id":source_id,"source_url":obj.get("url") or page,
      "extraction_method":"structured_event_data","publication_status":"candidate_review",
      "image_provenance":"external_ticket_listing_not_license"}
def main():
    cfg=json.loads(CFG.read_text(encoding="utf-8"))
    records=[];reports=[];seen=set()
    with requests.Session() as session:
        for source in cfg["sources"]:
            if not source.get("enabled"):continue
            pages=[c["url"] for c in source.get("cities",[]) if c.get("url") and c.get("slug") in CITIES]
            if not pages and source.get("homepage_url"):pages=[source["homepage_url"]]
            count=0;errors=[]
            for page in dict.fromkeys(pages):
                try:
                    r=session.get(page,headers=HEAD,timeout=20)
                    r.raise_for_status()
                    if not domain(r.url,source["domain"]):raise ValueError("unexpected_redirect")
                    soup=BeautifulSoup(r.text,"html.parser")
                    # Structured event data gives actual city, occurrence and images in one pass.
                    for obj in collect_jsonld(soup):
                        event=event_from_jsonld(obj,source["id"],r.url)
                        if not event:continue
                        key=(source["id"],event["source_url"],event["city"],event["date_time"])
                        if key in seen:continue
                        seen.add(key);records.append(event);count+=1
                    # Surface remaining pages as candidates only; never infer a local date from a listing.
                    for a in soup.select("a[href]"):
                        title=clean(a.get_text(" ",strip=True))[:160]
                        if len(title)<7 or len(title)>120 or any(x in title for x in GENERIC):continue
                        url=urljoin(r.url,a.get("href",""))
                        if not domain(url,source["domain"]):continue
                        context=clean(a.parent.get_text(" ",strip=True))[:250] if a.parent else title
                        city=next((k for k,names in CITIES.items() if any(n in context for n in names)),None)
                        if not city:continue
                        key=(source["id"],url,city,None)
                        if key in seen:continue
                        seen.add(key)
                        img=a.find("img")
                        image=(img.get("data-src") or img.get("src")) if img else None
                        records.append({"title":title,"city":city,"venue":None,"date_time":None,
                          "description":None,"image_url":urljoin(r.url,image) if image else None,
                          "video_url":None,"tickets_url":None,"category":None,"subcategory":None,
                          "source_id":source["id"],"source_url":url,
                          "extraction_method":"listing_candidate_requires_detail","publication_status":"candidate_review",
                          "image_provenance":"external_ticket_listing_not_license"})
                        count+=1
                        if count>=250:break
                except Exception as e:errors.append(type(e).__name__+": "+str(e)[:130])
                time.sleep(1)
            reports.append({"source_id":source["id"],"candidates":count,"errors":errors})
    output={"generated_at":datetime.now(timezone.utc).isoformat(),
      "scope":{"cities":list(CITIES),"categories":sorted(CATS)},
      "cms_modified":False,"public_site_modified":False,"needs_review":True,
      "counts":{"candidate_records":len(records),"structured_with_schedule":sum(x["extraction_method"]=="structured_event_data" for x in records)},
      "source_reports":reports,"events":records}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output["counts"],ensure_ascii=False))
if __name__=="__main__":main()

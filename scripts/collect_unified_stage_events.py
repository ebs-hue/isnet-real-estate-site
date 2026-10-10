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

STAGE_HINT=re.compile(r"הצג|מחזמר|מופע|סטנד.?אפ|הופע|קונצרט|תיאטרון|ילדים|זמר|קומדיה|מוזיקה|מחול|בידור",re.I)
EXCLUDE_TITLE=re.compile(r"^(?:ראשון לציון|אשדוד|ירושלים|תל אביב|באר שבע|פתח תקווה|Skip to content|← sababa\\.events)$",re.I)
EVENT_PATH=re.compile(r"/(?:event|events|show|shows|product|ticket|tickets|הופעות|הצגות)/",re.I)
SOURCE_CITY_URLS={
  "mevalim":{"ashdod":"https://www.mevalim.co.il/ashdod/","rishon-lezion":"https://www.mevalim.co.il/rishon-lezion/"},
  "makore":{"ashdod":"https://www.makore.co.il/browse/city/אשדוד","rishon-lezion":"https://www.makore.co.il/browse/city/ראשון-לציון"},
  "tickchak-live":{"ashdod":"https://live.tickchak.co.il/ashdod","rishon-lezion":"https://live.tickchak.co.il/rishon-lezion"},
  "sababa-events":{"ashdod":"https://sababa.events/he/venues/tsentr-stsenicheskikh-iskusstv-ashdod/"},
}
def detail_links(soup,base,host):
    links=[]
    for a in soup.select("a[href]"):
        url=urljoin(base,a.get("href",""))
        title=clean(a.get_text(" ",strip=True))
        if not domain(url,host) or url.rstrip("/")==base.rstrip("/"):continue
        if not (EVENT_PATH.search(urlparse(url).path) or STAGE_HINT.search(title)):continue
        if not (7<=len(title)<=125) or EXCLUDE_TITLE.match(title):continue
        if any(word in title for word in GENERIC):continue
        if url not in links:links.append(url)
        if len(links)>=75:break
    return links
def detail_extract(soup,source,page):
    rows=[]
    for obj in collect_jsonld(soup):
        event=event_from_jsonld(obj,source,page)
        if event and (STAGE_HINT.search(event["title"]) or STAGE_HINT.search(event.get("description") or "") or event.get("category") in CATS):rows.append(event)
    if not rows:return []
    image=txtmeta(soup,"og:image") or txtmeta(soup,"twitter:image")
    desc=txtmeta(soup,"og:description") or txtmeta(soup,"description")
    videos=[]
    for el in soup.select("iframe[src],a[href]"):
        v=el.get("src") or el.get("href") or ""
        if any(t in v for t in ("youtube.com/watch","youtube.com/embed","youtu.be/","vimeo.com/")):
            url=urljoin(page,v)
            if url not in videos:videos.append(url)
    for row in rows:
        if not row.get("image_url") and image:row["image_url"]=urljoin(page,image)
        if not row.get("description") and desc:row["description"]=desc
        if not row.get("video_url") and videos:row["video_url"]=videos[0]
        row["detail_page_fetched"]=True
    return rows

def main():
    cfg=json.loads(CFG.read_text(encoding="utf-8"))
    records=[];reports=[];seen=set()
    with requests.Session() as session:
        for source in cfg["sources"]:
            if source["id"] not in {"mevalim","tickchak-live","makore","sababa-events","tickchak-home","leaan","friends-hist"}:continue
            pages=[]
            for city in CITIES:
                url=SOURCE_CITY_URLS.get(source["id"],{}).get(city)
                if not url:
                    url=next((c.get("url") for c in source.get("cities",[]) if c.get("slug")==city),None)
                if url:pages.append((city,url))
            if not pages and source.get("homepage_url"):pages=[(None,source["homepage_url"])]
            count=0;errors=[];fetched=0
            for city_hint,page in pages:
                try:
                    response=session.get(page,headers=HEAD,timeout=20)
                    response.raise_for_status()
                    if not domain(response.url,source["domain"]):raise ValueError("unexpected_redirect")
                    soup=BeautifulSoup(response.text,"html.parser")
                    links=detail_links(soup,response.url,source["domain"])
                    # Structured event records only: never treat navigation links as performances.
                    for event in detail_extract(soup,source["id"],response.url):
                        if event.get("city") not in CITIES:continue
                        key=(source["id"],event["title"],event["city"],event["date_time"])
                        if key in seen:continue
                        seen.add(key);records.append(event);count+=1
                    for url in links:
                        if fetched>=65:break
                        try:
                            detail=session.get(url,headers=HEAD,timeout=18)
                            detail.raise_for_status()
                            if not domain(detail.url,source["domain"]):continue
                            detail_soup=BeautifulSoup(detail.text,"html.parser")
                            for event in detail_extract(detail_soup,source["id"],detail.url):
                                if event.get("city") not in CITIES:continue
                                key=(source["id"],event["title"],event["city"],event["date_time"])
                                if key in seen:continue
                                seen.add(key);records.append(event);count+=1
                            fetched+=1
                        except requests.RequestException as exc:errors.append(type(exc).__name__+": "+str(exc)[:80])
                        time.sleep(.4)
                except Exception as exc:errors.append(type(exc).__name__+": "+str(exc)[:120])
                time.sleep(.6)
            reports.append({"source_id":source["id"],"candidates":count,"details_fetched":fetched,"errors":errors[:6]})
    output={"generated_at":datetime.now(timezone.utc).isoformat(),
      "scope":{"cities":list(CITIES),"categories":sorted(CATS)},
      "cms_modified":False,"public_site_modified":False,"needs_review":True,
      "counts":{"candidate_records":len(records),"structured_with_schedule":sum(bool(x.get("date_time") and x.get("venue")) for x in records),"with_images":sum(bool(x.get("image_url")) for x in records),"with_videos":sum(bool(x.get("video_url")) for x in records)},
      "source_reports":reports,"events":records}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output["counts"],ensure_ascii=False))
if __name__=="__main__":main()

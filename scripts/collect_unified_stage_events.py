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
    return host==root or host.endswith("."+root) or (root=="mevalim.co.il" and host=="tickets.mevalim.co.il")
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
    if isinstance(image,str) and any(x in image.lower() for x in ("big_star.png","logo","placeholder","default-image","no-image")):image=None
    description=clean(obj.get("description"))
    if any(x in description for x in ("באתר מבלים ריכזנו","מחפשים הופעות","לוח הופעות באשדוד עם מבצעים")):description=None
    return {"title":name,"city":found_city,"venue":loc or None,"date_time":obj.get("startDate"),
      "end_time":obj.get("endDate"),"description":description,
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
        if re.fullmatch(r"[\\w\\s]+",title) and any(x in title for x in ("הצג הכול","בחרו עיר","לוח הופעות")):continue
        if any(word in title for word in GENERIC):continue
        if url not in links:links.append(url)
        if len(links)>=75:break
    return links

def mevalim_ticket_extract(soup,page):
    if (urlparse(page).hostname or "")!="tickets.mevalim.co.il":return []
    heading=soup.find("h1")
    title=clean(heading.get_text(" ",strip=True)) if heading else ""
    if not title or len(title)>140:return []
    raw=soup.get_text(" ",strip=True)
    hit=re.search(r"(\\d{1,2}:\\d{2})\\s*[·•|]\\s*(?:יום\\s*)?[^·•|]{0,15}[·•|]\\s*(\\d{1,2}\\.\\d{1,2}\\.20\\d{2})\\s*[·•|]\\s*([^·•|]{4,100})",raw)
    if not hit:return []
    clock,day,venue=hit.groups()
    city=next((k for k,names in CITIES.items() if any(n in venue for n in names)),None)
    if not city:return []
    d,m,y=day.split(".")
    details=[]
    about=soup.find(string=re.compile(r"אודות האירוע"))
    if about:
        block=about.find_parent(["section","article","div"])
        if block:details.append(clean(block.get_text(" ",strip=True))[:5000])
    img=txtmeta(soup,"og:image") or txtmeta(soup,"twitter:image")
    if not img:
        candidates=[i.get("src") or i.get("data-src") for i in soup.select("img[src],img[data-src]") if i.get("src") or i.get("data-src")]
        img=next((x for x in candidates if "youtube" not in x and "logo" not in x and not x.startswith("data:")),None)
    videos=[]
    for a in soup.select("iframe[src],a[href],img[src]"):
        v=a.get("src") or a.get("href") or ""
        m=re.search(r"(?:img\\.youtube\\.com/vi/|youtube\\.com/embed/|youtu\\.be/)([a-zA-Z0-9_-]{11})",v)
        if m:videos.append("https://www.youtube.com/watch?v="+m.group(1))
    return [{"title":title,"city":city,"venue":venue,"date_time":f"{y}-{m.zfill(2)}-{d.zfill(2)}T{clock}:00",
             "end_time":None,"description":details[0] if details else txtmeta(soup,"description"),
             "image_url":urljoin(page,img) if img else None,"video_url":videos[0] if videos else None,
             "tickets_url":page,"category":None,"subcategory":None,"source_id":"mevalim","source_url":page,
             "extraction_method":"ticket_detail_page","publication_status":"candidate_review",
             "image_provenance":"external_ticket_listing_not_license"}]

def detail_extract(soup,source,page):
    if source=="mevalim" and (urlparse(page).hostname or "")=="tickets.mevalim.co.il":
        return mevalim_ticket_extract(soup,page)
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
        if row.get("image_url") and any(t in row["image_url"].lower() for t in ("big_star.png","logo","placeholder","default-image")):row["image_url"]=None
        if row.get("description") and ("באתר מבלים ריכזנו" in row["description"] or "מחפשים הופעות" in row["description"]):row["description"]=None
        if not row.get("image_url") and image and not any(t in image.lower() for t in ("big_star.png","logo","placeholder","default-image")):row["image_url"]=urljoin(page,image)
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
    # Detect overlapping listings without discarding evidence from different sites.
    from collections import defaultdict,Counter
    by_occurrence=defaultdict(list)
    video_uses=defaultdict(set)
    for row in records:
        if row.get("video_url"):
            video_uses[row["video_url"]].add((row.get("title"),row.get("city"),row.get("date_time")))
        identity=(row.get("city"),clean(row.get("venue")).casefold(),str(row.get("date_time") or "")[:16])
        if all(identity):by_occurrence[identity].append(row)
    repeated_videos={url for url,identities in video_uses.items() if len(identities)>1}
    for row in records:
        if row.get("image_url") and any(x in row["image_url"].lower() for x in ("big_star.png","placeholder","default-image","no-image")):row["image_url"]=None
        if row.get("description") and any(x in row["description"] for x in ("באתר מבלים ריכזנו","מחפשים הופעות")):row["description"]=None
        if row.get("video_url") in repeated_videos:
            row["video_candidate_needs_review"]=True
            row["video_url"]=None
    possible_duplicates=[
        {"city":key[0],"venue":key[1],"date_time":key[2],
         "events":[{"title":r["title"],"source_id":r["source_id"],"source_url":r["source_url"]} for r in group]}
        for key,group in by_occurrence.items() if len(group)>1
    ]
    quality={"with_description":sum(bool(x.get("description")) for x in records),
             "with_image":sum(bool(x.get("image_url")) for x in records),
             "with_ticket_url":sum(bool(x.get("tickets_url")) for x in records),
             "with_video_after_cross_show_check":sum(bool(x.get("video_url")) for x in records),
             "video_urls_suppressed_as_shared":len(repeated_videos),
             "possible_duplicate_occurrence_groups":len(possible_duplicates)}
    output={"generated_at":datetime.now(timezone.utc).isoformat(),
      "scope":{"cities":list(CITIES),"categories":sorted(CATS)},
      "cms_modified":False,"public_site_modified":False,"needs_review":True,
      "counts":{"candidate_records":len(records),"structured_with_schedule":sum(bool(x.get("date_time") and x.get("venue")) for x in records),"with_images":sum(bool(x.get("image_url")) for x in records),"with_videos":sum(bool(x.get("video_url")) for x in records)},
      "source_reports":reports,"quality":quality,"possible_duplicates":possible_duplicates,"events":records}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output["counts"],ensure_ascii=False))
if __name__=="__main__":main()

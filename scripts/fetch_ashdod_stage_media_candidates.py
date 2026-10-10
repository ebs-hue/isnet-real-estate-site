#!/usr/bin/env python3
"""Fetch show-specific editorial/media candidates for matched Ashdod stage events.
Read only. Preserve source attribution, never replace public content on guesswork.
"""
import json,re,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview/admin/data"
IN=DATA/"event-enrichment-candidates-ashdod.json"
OUT=DATA/"stage-content-media-review-ashdod.json"
CATS={"music","standup","kids","theatre"}
HEAD={"User-Agent":"ISNET-Events-Enrichment/1.0 (isnet.co.il)","Accept-Language":"he-IL,he;q=0.9"}
def clean(s):
    return re.sub(r"\s+"," ",str(s or "")).strip()
def meta(soup,property_name):
    found=soup.find("meta",attrs={"property":property_name}) or soup.find("meta",attrs={"name":property_name})
    return clean(found.get("content")) if found else None
def extract(session,url):
    response=session.get(url,headers=HEAD,timeout=18)
    response.raise_for_status()
    requested=urlparse(url).hostname or ""
    landed=urlparse(response.url).hostname or ""
    if landed!=requested and not landed.endswith("."+requested) and not requested.endswith("."+landed):
        raise ValueError("source_redirected_offsite")
    soup=BeautifulSoup(response.text,"html.parser")
    image=meta(soup,"og:image") or meta(soup,"twitter:image")
    desc=meta(soup,"og:description") or meta(soup,"description")
    title=meta(soup,"og:title") or (clean(soup.title.get_text(" ",strip=True)) if soup.title else None)
    videos=[]
    for node in soup.select("iframe[src],a[href]"):
        href=node.get("src") or node.get("href") or ""
        if any(host in href for host in ("youtube.com/watch","youtube.com/embed/","youtu.be/","vimeo.com/")):
            value=urljoin(response.url,href)
            if value not in videos:videos.append(value)
        if len(videos)>=4:break
    return {"fetched_url":response.url,"source_title":title,"description_candidate":desc,
            "image_candidate_url":urljoin(response.url,image) if image else None,
            "video_candidates":videos,"classification_candidate":None,
            "image_rights_status":"unverified","publication_status":"review_required"}

def main():
    feed=json.loads(IN.read_text(encoding="utf-8"))["events"]
    result=[];cache={}
    with requests.Session() as session:
        for event in feed:
            if event.get("category") not in CATS:continue
            proposals=[]
            seen=set()
            for source in event.get("same_production_candidates",[]):
                url=source.get("source_url")
                if not url or url in seen:continue
                seen.add(url)
                try:
                    if url not in cache:
                        cache[url]=extract(session,url)
                        time.sleep(1)
                    detail={"source_id":source.get("source_id"),"source_url":url,**cache[url]}
                except Exception as exc:
                    detail={"source_id":source.get("source_id"),"source_url":url,"fetch_error":str(exc)[:170]}
                proposals.append(detail)
            if proposals:
                result.append({"event_id":event.get("event_id"),"title":event.get("title"),
                               "category":event.get("category"),"subcategory":event.get("subcategory"),
                               "source_candidates":proposals,
                               "never_replace_existing_verified_image_without_identity_check":True})
    output={"generated_at":datetime.now(timezone.utc).isoformat(),"scope":"ashdod_stage_only",
            "events_with_source_matches":len(result),"cms_modified":False,"public_site_modified":False,
            "events":result}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Stage events with reviewable media candidates",len(result))
if __name__=="__main__":main()

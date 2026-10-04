#!/usr/bin/env python3
from __future__ import annotations

import difflib
import html
import json
import re
import ssl
import time
import unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview"/"ashdod"/"data"/"events.json"
REPORT=ROOT/"events-preview"/"ashdod"/"data"/"image-enrichment-report.json"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
TIMEOUT=22
PAUSE=.10

GENERIC=(
    "/languages/il.gif","artistshadow","/images/live/more/eventnew.jpg",
    "placeholder","no-image","no_image","noimage","blank.gif","spacer.gif",
    "transparent.gif","favicon","/logo.","/logo/","/icons/","/icon/"
)
EVENT_SIGNALS=("/uploads/","/thumbs/","/caps/","livenew_","/events/","/event/","poster","banner")

def norm(s:str)->str:
    s=html.unescape(s or "")
    s=unicodedata.normalize("NFKC",s)
    s=s.replace("־","-").replace("–","-").replace("—","-")
    s=re.sub(r"[\u0591-\u05C7]","",s)
    s=re.sub(r"[^0-9A-Za-zא-ת]+"," ",s.lower())
    return re.sub(r"\s+"," ",s).strip()

def tokens(s:str)->set[str]:
    return {x for x in norm(s).split() if len(x)>1}

def host_family(a:str,b:str)->bool:
    x=(urlparse(a).hostname or "").lower().removeprefix("www.")
    y=(urlparse(b).hostname or "").lower().removeprefix("www.")
    return bool(x and y and (x==y or x.endswith("."+y) or y.endswith("."+x)))

def qurl(url:str)->str:
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))

def fetch(url:str, referer:Optional[str]=None, limit:Optional[int]=None)->Tuple[bytes,str,str]:
    target=qurl(url)
    headers={"User-Agent":UA,"Accept-Language":"he-IL,he;q=.9,en;q=.7","Referer":qurl(referer or url)}
    if limit:
        headers["Range"]=f"bytes=0-{limit-1}"
    req=Request(target,headers=headers)
    with urlopen(req,timeout=TIMEOUT,context=ssl.create_default_context()) as r:
        return r.read(limit or -1),(r.headers.get("Content-Type") or "").lower(),r.geturl()

def fetch_html(url:str)->Tuple[str,str]:
    raw,ctype,final=fetch(url)
    m=re.search(r"charset=([\w-]+)",ctype)
    enc=m.group(1) if m else "utf-8"
    try: txt=raw.decode(enc,errors="replace")
    except LookupError: txt=raw.decode("utf-8",errors="replace")
    return txt,final

def generic(url:str)->bool:
    low=html.unescape(url or "").lower()
    return (not low) or any(x in low for x in GENERIC)

def event_signal(url:str)->bool:
    low=html.unescape(url or "").lower()
    return any(x in low for x in EVENT_SIGNALS)

def verify_image(url:str,referer:str)->bool:
    if generic(url): return False
    try:
        raw,ctype,_=fetch(url,referer=referer,limit=131072)
        if ctype.startswith("image/"): return len(raw)>800
        return len(raw)>800 and (
            raw.startswith(b"\xff\xd8\xff") or
            raw.startswith(b"\x89PNG\r\n\x1a\n") or
            (raw.startswith(b"RIFF") and b"WEBP" in raw[:16])
        )
    except Exception:
        return False

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
        self.images=[]
        self.meta=[]
        self.styles=[]
        self.href=None
        self.text=[]
    def handle_starttag(self,tag,attrs):
        a={str(k).lower():(v or "") for k,v in attrs}
        tag=tag.lower()
        if tag=="a":
            self.href=a.get("href"); self.text=[]
        elif tag in ("img","source"):
            self.images.append(a)
        elif tag=="meta":
            self.meta.append(a)
        if a.get("style"): self.styles.append(a)
    def handle_data(self,data):
        if self.href is not None: self.text.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=="a" and self.href is not None:
            self.links.append((self.href,re.sub(r"\s+"," "," ".join(self.text)).strip()))
            self.href=None; self.text=[]

def parse(markup:str)->P:
    p=P()
    try:p.feed(markup)
    except Exception:pass
    return p

def link_score(title:str,text:str,href:str)->float:
    a,b=norm(title),norm(text)
    if not a:return 0
    score=5*difflib.SequenceMatcher(None,a,b).ratio()
    if a==b:score+=12
    if a and b and a in b:score+=8
    ta,tb=tokens(title),tokens(text)
    if ta:score+=6*len(ta&tb)/len(ta)
    if norm(title).replace(" ","") in norm(href).replace(" ",""):score+=3
    return score

def detail_links(title:str,base:str,markup:str)->List[str]:
    ranked=[]
    for href,text in parse(markup).links:
        if not href or href.startswith(("#","javascript:","mailto:","tel:")):continue
        u=urljoin(base,href)
        if not host_family(base,u):continue
        s=link_score(title,text,href)
        if s>=5.0:ranked.append((s,u.split("#",1)[0]))
    ranked.sort(key=lambda x:(-x[0],len(x[1])))
    out=[]
    for _,u in ranked:
        if u not in out:out.append(u)
        if len(out)>=5:break
    return out

def image_sources(attrs:Dict[str,str],base:str)->List[str]:
    vals=[]
    for k in ("src","data-src","data-original","data-lazy-src","data-image","data-url"):
        if attrs.get(k):vals.append(attrs[k])
    for k in ("srcset","data-srcset"):
        if attrs.get(k):
            parts=[x.strip().split(" ")[0] for x in attrs[k].split(",") if x.strip()]
            if parts:vals.append(parts[-1])
    return [urljoin(base,html.unescape(v)) for v in vals if v and not v.startswith(("data:","blob:"))]

def candidates(title:str,page:str,markup:str)->List[Tuple[float,str,str]]:
    p=parse(markup); out=[]
    def add(u:str,score:float,why:str):
        u=urljoin(page,html.unescape((u or "").strip().strip("'\"")))
        if generic(u):return
        if event_signal(u):score+=45
        low=u.lower()
        if "/uploads/" in low:score+=30
        if "/thumbs/" in low or "/caps/" in low:score+=18
        out.append((score,u,why))

    for m in p.meta:
        key=(m.get("property") or m.get("name") or "").lower()
        content=m.get("content") or ""
        if key in ("og:image","og:image:url","twitter:image","twitter:image:src") and content:add(content,100,key)
        if (m.get("itemprop") or "").lower()=="image" and content:add(content,92,"itemprop")

    tt=tokens(title); nt=norm(title)
    for attrs in p.images:
        alt=" ".join(filter(None,[attrs.get("alt"),attrs.get("title"),attrs.get("aria-label")]))
        na=norm(alt)
        for u in image_sources(attrs,page):
            low=u.lower()
            if any(x in low for x in ("logo","icon","sprite","spinner","loader","calendar","facebook","instagram")) and not event_signal(u):continue
            score=25
            if nt and na:score+=20*difflib.SequenceMatcher(None,nt,na).ratio()
            if nt and na and nt in na:score+=35
            at=tokens(alt)
            if tt:score+=25*len(tt&at)/len(tt)
            add(u,score,"img")

    for attrs in p.styles:
        for m in re.finditer(r"url\(([^)]+)\)",html.unescape(attrs.get("style") or ""),re.I):
            add(m.group(1),48,"css")

    decoded=html.unescape(markup)
    pats=(
        r'''https?://[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
        r'''//[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
        r'''/[^"'<>\s\\]*(?:uploads|caps|events?)[^"'<>\s\\]*\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?'''
    )
    for pat in pats:
        for m in re.finditer(pat,decoded,re.I):add(m.group(0),42,"raw")

    best={}
    for score,u,why in out:
        if u not in best or score>best[u][0]:best[u]=(score,u,why)
    return sorted(best.values(),reverse=True)

def main()->int:
    payload=json.loads(DATA.read_text(encoding="utf-8"))
    events=payload.get("events") or []
    stats=Counter()
    failures=[]
    roots={}
    pages={}
    title_cache={}

    # Clear known generic assets left by previous pass.
    for e in events:
        if e.get("image_url") and generic(e["image_url"]):
            e["image_url"]=None
            e["image_source"]=None
            e["image_credit"]=None
            e["image_publishable"]=False
            stats["generic_images_cleared"]+=1

    def cached(url:str,cache:dict):
        if url in cache:return cache[url]
        try:
            time.sleep(PAUSE)
            cache[url]=fetch_html(url)
        except Exception:
            cache[url]=None
        return cache[url]

    for i,e in enumerate(events,1):
        if e.get("image_url") and e.get("image_publishable") is True:
            stats["kept_existing"]+=1
            continue
        title=e.get("title") or ""
        sources=[x.get("url") for x in e.get("sources",[]) if x.get("url")]
        if not sources:
            failures.append({"event_id":e.get("event_id"),"title":title,"reason":"no_source"});continue
        ck=(norm(title),tuple(sorted(urlparse(x).hostname or "" for x in sources)))
        if ck in title_cache:
            u,src=title_cache[ck]
            e["image_url"]=u;e["image_source"]=src;e["image_publishable"]=True
            stats["reused_by_title"]+=1;continue

        detail=[]
        if e.get("ticket_url"):detail.append(e["ticket_url"])
        for root in sources:
            loaded=cached(root,roots)
            if not loaded:continue
            markup,final=loaded
            for u in detail_links(title,final,markup):
                if u not in detail:detail.append(u)

        selected=None;tried=[]
        for u in detail[:5]:
            if not any(host_family(u,s) for s in sources):
                continue
            loaded=cached(u,pages)
            if not loaded:
                tried.append({"url":u,"status":"fetch_failed"});continue
            markup,final=loaded
            cs=candidates(title,final,markup)
            tried.append({"url":final,"top_candidates":[{"url":x[1],"score":round(x[0],1),"reason":x[2]} for x in cs[:5]]})
            for score,img,why in cs[:12]:
                ok=verify_image(img,final)
                trusted=event_signal(img) and score>=70
                if ok or trusted:
                    selected=(img,final);break
            if selected:break

        if selected:
            img,src=selected
            e["image_url"]=img;e["image_source"]=src;e["image_publishable"]=True
            if not e.get("ticket_url"):e["ticket_url"]=src
            title_cache[ck]=selected
            stats["enriched"]+=1
            print(f"[{i:03d}/{len(events)}] IMAGE {title} -> {img}")
        else:
            stats["missing"]+=1
            failures.append({"event_id":e.get("event_id"),"title":title,"sources":sources,"tried":tried})
            print(f"[{i:03d}/{len(events)}] MISS {title}")

    missing=[e for e in events if not(e.get("image_url") and e.get("image_publishable") is True)]
    by_source=Counter();by_cat=Counter()
    for e in missing:
        by_cat[e.get("category") or "unknown"]+=1
        for s in e.get("sources",[]):by_source[s.get("name") or "unknown"]+=1
    report={
        "generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "total_events":len(events),
        "events_with_publishable_images":len(events)-len(missing),
        "events_still_missing_images":len(missing),
        "stats":dict(stats),
        "missing_by_source":dict(by_source),
        "missing_by_category":dict(by_cat),
        "missing":failures
    }
    DATA.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="missing"},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

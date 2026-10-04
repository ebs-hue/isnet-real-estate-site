#!/usr/bin/env python3
from __future__ import annotations
import difflib, html, json, re, ssl, time, unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview"/"ashdod"/"data"/"events.json"
REPORT=ROOT/"events-preview"/"ashdod"/"data"/"image-enrichment-report.json"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
GENERIC=("/languages/il.gif","artistshadow","/images/live/more/eventnew.jpg","eventnew.jpg","placeholder","no-image","no_image","noimage","no_pic","no-pic","blank.gif","spacer.gif","transparent.gif","favicon","/logo.","/logo/","/icons/","/icon/")
SIGNALS=("/uploads/","/thumbs/","/caps/","livenew_","updateartistimage","/events/","/event/","poster","banner")

def norm(s):
    s=html.unescape(s or "")
    s=unicodedata.normalize("NFKC",s).replace("־","-").replace("–","-").replace("—","-")
    s=re.sub(r"[\u0591-\u05C7]","",s)
    return re.sub(r"\s+"," ",re.sub(r"[^0-9A-Za-zא-ת]+"," ",s.lower())).strip()

def toks(s): return {x for x in norm(s).split() if len(x)>1}

def same_host(a,b):
    x=(urlparse(a).hostname or "").lower().removeprefix("www.")
    y=(urlparse(b).hostname or "").lower().removeprefix("www.")
    return bool(x and y and (x==y or x.endswith("."+y) or y.endswith("."+x)))

def safe_url(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))

def fetch(url,referer=None,limit=None):
    headers={"User-Agent":UA,"Accept-Language":"he-IL,he;q=.9,en;q=.7","Referer":safe_url(referer or url)}
    if limit: headers["Range"]=f"bytes=0-{limit-1}"
    with urlopen(Request(safe_url(url),headers=headers),timeout=22,context=ssl.create_default_context()) as r:
        return r.read(limit or -1),(r.headers.get("Content-Type") or "").lower(),r.geturl()

def get_html(url):
    raw,ctype,final=fetch(url)
    m=re.search(r"charset=([\w-]+)",ctype)
    enc=m.group(1) if m else "utf-8"
    try:return raw.decode(enc,errors="replace"),final
    except LookupError:return raw.decode("utf-8",errors="replace"),final

def generic(url):
    low=html.unescape(url or "").lower()
    return not low or any(x in low for x in GENERIC)

def signal(url):
    low=html.unescape(url or "").lower()
    return any(x in low for x in SIGNALS)

def verify(url,ref):
    if generic(url): return False
    try:
        raw,ctype,_=fetch(url,ref,131072)
        if ctype.startswith("image/"): return len(raw)>800
        return len(raw)>800 and (raw.startswith(b"\xff\xd8\xff") or raw.startswith(b"\x89PNG\r\n\x1a\n") or (raw.startswith(b"RIFF") and b"WEBP" in raw[:16]))
    except Exception:return False

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]; self.images=[]; self.meta=[]; self.styles=[]
        self.href=None; self.text=[]; self.media=[]
    def handle_starttag(self,tag,attrs):
        a={str(k).lower():(v or "") for k,v in attrs}; tag=tag.lower()
        if tag=="a":
            self.href=a.get("href"); self.text=[]; self.media=[]
        elif tag in ("img","source"):
            self.images.append(a)
            if self.href is not None:self.media.append(a)
        elif tag=="meta": self.meta.append(a)
        if a.get("style"):
            self.styles.append(a)
            if self.href is not None:self.media.append(a)
    def handle_data(self,data):
        if self.href is not None:self.text.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=="a" and self.href is not None:
            self.links.append((self.href,re.sub(r"\s+"," "," ".join(self.text)).strip(),list(self.media)))
            self.href=None; self.text=[]; self.media=[]

def parse(markup):
    p=Parser()
    try:p.feed(markup)
    except Exception:pass
    return p

def score_link(title,text,href):
    a,b=norm(title),norm(text)
    if not a:return 0
    s=5*difflib.SequenceMatcher(None,a,b).ratio()
    if a==b:s+=12
    if a and b and a in b:s+=8
    ta,tb=toks(title),toks(text)
    if ta:s+=6*len(ta&tb)/len(ta)
    if a.replace(" ","") in norm(href).replace(" ",""):s+=3
    return s

def media_urls(attrs,base):
    vals=[]
    for k in ("src","data-src","data-original","data-lazy-src","data-image","data-url"):
        if attrs.get(k):vals.append(attrs[k])
    for k in ("srcset","data-srcset"):
        if attrs.get(k):
            parts=[x.strip().split(" ")[0] for x in attrs[k].split(",") if x.strip()]
            if parts:vals.append(parts[-1])
    style=html.unescape(attrs.get("style") or "")
    vals += [m.group(1).strip().strip("'\"") for m in re.finditer(r"url\(([^)]+)\)",style,re.I)]
    return [urljoin(base,html.unescape(v)) for v in vals if v and not v.startswith(("data:","blob:"))]

def matches(title,base,markup):
    ranked=[]
    for href,text,media in parse(markup).links:
        if not href or href.startswith(("#","javascript:","mailto:","tel:")):continue
        u=urljoin(base,href)
        if not same_host(base,u):continue
        s=score_link(title,text,href)
        if s>=5:ranked.append((s,u.split("#",1)[0],media))
    ranked.sort(key=lambda x:(-x[0],len(x[1])))
    out=[];seen=set()
    for s,u,media in ranked:
        if u in seen:continue
        seen.add(u);out.append((u,media,s))
        if len(out)>=5:break
    return out

def page_candidates(title,page,markup):
    p=parse(markup); out=[]
    def add(u,score,why):
        u=urljoin(page,html.unescape((u or "").strip().strip("'\"")))
        if generic(u):return
        if signal(u):score+=45
        low=u.lower()
        if "/uploads/" in low:score+=30
        if "/thumbs/" in low or "/caps/" in low:score+=18
        out.append((score,u,why))
    for m in p.meta:
        key=(m.get("property") or m.get("name") or "").lower(); val=m.get("content") or ""
        if key in ("og:image","og:image:url","twitter:image","twitter:image:src") and val:add(val,100,key)
        if (m.get("itemprop") or "").lower()=="image" and val:add(val,92,"itemprop")
    nt=norm(title); tt=toks(title)
    for attrs in p.images:
        alt=" ".join(filter(None,[attrs.get("alt"),attrs.get("title"),attrs.get("aria-label")]))
        na=norm(alt)
        for u in media_urls(attrs,page):
            score=25
            if nt and na:score+=20*difflib.SequenceMatcher(None,nt,na).ratio()
            if nt and na and nt in na:score+=35
            at=toks(alt)
            if tt:score+=25*len(tt&at)/len(tt)
            add(u,score,"img")
    decoded=html.unescape(markup)
    for pat in (
        r'''https?://[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
        r'''//[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
        r'''/[^"'<>\s\\]*(?:uploads|caps|events?)[^"'<>\s\\]*\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?'''
    ):
        for m in re.finditer(pat,decoded,re.I):add(m.group(0),42,"raw")
    best={}
    for row in out:
        if row[1] not in best or row[0]>best[row[1]][0]:best[row[1]]=row
    return sorted(best.values(),reverse=True)

def main():
    payload=json.loads(DATA.read_text(encoding="utf-8")); events=payload.get("events") or []
    stats=Counter(); failures=[]; roots={}; pages={}; title_cache={}
    for e in events:
        if e.get("image_url") and generic(e["image_url"]):
            e["image_url"]=None;e["image_source"]=None;e["image_credit"]=None;e["image_publishable"]=False
            stats["generic_images_cleared"]+=1

    def cached(url,cache):
        if url in cache:return cache[url]
        try:
            time.sleep(.10); cache[url]=get_html(url)
        except Exception:cache[url]=None
        return cache[url]

    for i,e in enumerate(events,1):
        if e.get("image_url") and e.get("image_publishable") is True:
            stats["kept_existing"]+=1;continue
        title=e.get("title") or ""; sources=[x.get("url") for x in e.get("sources",[]) if x.get("url")]
        if not sources:
            failures.append({"event_id":e.get("event_id"),"title":title,"reason":"no_source"});continue
        ck=(norm(title),tuple(sorted(urlparse(x).hostname or "" for x in sources)))
        if ck in title_cache:
            img,src=title_cache[ck];e["image_url"]=img;e["image_source"]=src;e["image_publishable"]=True
            stats["reused_by_title"]+=1;continue

        detail=[]; listing=[]
        if e.get("ticket_url"):detail.append(e["ticket_url"])
        for root in sources:
            loaded=cached(root,roots)
            if not loaded:continue
            markup,final=loaded
            for u,media,match_score in matches(title,final,markup):
                if u not in detail:detail.append(u)
                for attrs in media:
                    for img in media_urls(attrs,final):
                        if not generic(img):listing.append((match_score+70,img,final,u))

        selected=None; tried=[]
        listing.sort(key=lambda x:-x[0])
        for score,img,root,event_url in listing[:15]:
            if verify(img,root) or (signal(img) and score>=70):
                selected=(img,event_url);stats["from_source_listing"]+=1
                if not e.get("ticket_url"):e["ticket_url"]=event_url
                break

        if not selected:
            for u in detail[:5]:
                if not any(same_host(u,s) for s in sources):continue
                loaded=cached(u,pages)
                if not loaded:
                    tried.append({"url":u,"status":"fetch_failed"});continue
                markup,final=loaded; cs=page_candidates(title,final,markup)
                tried.append({"url":final,"top_candidates":[{"url":x[1],"score":round(x[0],1),"reason":x[2]} for x in cs[:5]]})
                for score,img,why in cs[:12]:
                    if verify(img,final) or (signal(img) and score>=70):
                        selected=(img,final);break
                if selected:
                    if not e.get("ticket_url"):e["ticket_url"]=final
                    break

        if selected:
            img,src=selected;e["image_url"]=img;e["image_source"]=src;e["image_publishable"]=True
            title_cache[ck]=selected;stats["enriched"]+=1
            print(f"[{i:03d}/{len(events)}] IMAGE {title} -> {img}")
        else:
            stats["missing"]+=1;failures.append({"event_id":e.get("event_id"),"title":title,"sources":sources,"tried":tried})
            print(f"[{i:03d}/{len(events)}] MISS {title}")

    missing=[e for e in events if not(e.get("image_url") and e.get("image_publishable") is True)]
    bs=Counter();bc=Counter()
    for e in missing:
        bc[e.get("category") or "unknown"]+=1
        for s in e.get("sources",[]):bs[s.get("name") or "unknown"]+=1
    report={"generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"total_events":len(events),"events_with_publishable_images":len(events)-len(missing),"events_still_missing_images":len(missing),"stats":dict(stats),"missing_by_source":dict(bs),"missing_by_category":dict(bc),"missing":failures}
    DATA.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="missing"},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())

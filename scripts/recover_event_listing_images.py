#!/usr/bin/env python3
from __future__ import annotations
import difflib, html, json, re, ssl, time, unicodedata
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview"/"ashdod"/"data"/"events.json"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
BAD=("no_pic","no-pic","placeholder","smarticket_logo","_logo_","/languages/","artistshadow","eventnew.jpg","favicon","sprite","spinner")
SIGNALS=("/uploads/","/thumbs/","/caps/","livenew_","updateartistimage")

def norm(s):
    s=html.unescape(s or "")
    s=unicodedata.normalize("NFKC",s).replace("־","-").replace("–","-").replace("—","-")
    s=re.sub(r"[\u0591-\u05C7]","",s)
    return re.sub(r"\s+"," ",re.sub(r"[^0-9A-Za-zא-ת]+"," ",s.lower())).strip()

def tok(s): return {x for x in norm(s).split() if len(x)>1}

def qurl(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))

def fetch(url,ref=None,limit=None):
    h={"User-Agent":UA,"Accept-Language":"he-IL,he;q=.9,en;q=.7","Referer":qurl(ref or url)}
    if limit:h["Range"]=f"bytes=0-{limit-1}"
    with urlopen(Request(qurl(url),headers=h),timeout=25,context=ssl.create_default_context()) as r:
        return r.read(limit or -1),(r.headers.get("Content-Type") or "").lower(),r.geturl()

def get_html(url):
    raw,ctype,final=fetch(url)
    m=re.search(r"charset=([\w-]+)",ctype)
    enc=m.group(1) if m else "utf-8"
    try:return raw.decode(enc,errors="replace"),final
    except LookupError:return raw.decode("utf-8",errors="replace"),final

def bad(url):
    low=html.unescape(url or "").lower()
    return not low or any(x in low for x in BAD)

def verify(url,ref):
    if bad(url):return False
    try:
        raw,ctype,_=fetch(url,ref,131072)
        if ctype.startswith("image/"):return len(raw)>800
        return len(raw)>800 and (raw.startswith(b"\xff\xd8\xff") or raw.startswith(b"\x89PNG\r\n\x1a\n") or (raw.startswith(b"RIFF") and b"WEBP" in raw[:16]))
    except Exception:return False

class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.rows=[];self.href=None;self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=="a":
            a={str(k).lower():(v or "") for k,v in attrs};self.href=a.get("href");self.text=[]
    def handle_data(self,data):
        if self.href is not None:self.text.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=="a" and self.href is not None:
            self.rows.append((self.href,re.sub(r"\s+"," "," ".join(self.text)).strip()))
            self.href=None;self.text=[]

def parse_links(markup):
    p=Links()
    try:p.feed(markup)
    except Exception:pass
    return p.rows

def link_score(title,text,href):
    a,b=norm(title),norm(text)
    if not a:return 0
    score=5*difflib.SequenceMatcher(None,a,b).ratio()
    if a==b:score+=12
    if a and b and a in b:score+=8
    ta,tb=tok(title),tok(text)
    if ta:score+=6*len(ta&tb)/len(ta)
    if a.replace(" ","") in norm(href).replace(" ",""):score+=3
    return score

def image_urls(chunk,base):
    decoded=html.unescape(chunk)
    found=[]
    patterns=(
      r'''https?://[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
      r'''//[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
      r'''/[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?'''
    )
    for pat in patterns:
        for m in re.finditer(pat,decoded,re.I):
            u=urljoin(base,m.group(0))
            if bad(u):continue
            low=u.lower();score=0
            if "/thumbs/" in low:score+=100
            if "/uploads/" in low:score+=70
            if "/caps/" in low:score+=90
            if "livenew_" in low or "updateartistimage" in low:score+=80
            if any(x in low for x in ("logo","icon","language","flag")):score-=100
            found.append((score,u))
    best={}
    for score,u in found:
        best[u]=max(score,best.get(u,-999))
    return sorted(((s,u) for u,s in best.items()),reverse=True)

def main():
    data=json.loads(DATA.read_text(encoding="utf-8"))
    events=data.get("events",[])
    roots={}
    recovered=0
    for e in events:
        if e.get("image_url") and e.get("image_publishable") is True:continue
        title=e.get("title") or ""
        source_urls=[s.get("url") for s in e.get("sources",[]) if s.get("url")]
        best=None
        for root in source_urls:
            if root not in roots:
                try:roots[root]=get_html(root)
                except Exception:roots[root]=None
            loaded=roots[root]
            if not loaded:continue
            markup,final=loaded
            ranked=[]
            for href,text in parse_links(markup):
                if not href:continue
                score=link_score(title,text,href)
                if score>=5:ranked.append((score,href,urljoin(final,href)))
            ranked.sort(reverse=True)
            for linkscore,raw_href,event_url in ranked[:4]:
                probes=[raw_href,html.escape(raw_href,quote=True)]
                q=urlparse(event_url).query
                mid=re.search(r"(?:^|&)id=([^&]+)",q)
                if mid:probes.append("id="+mid.group(1))
                positions=[]
                for probe in probes:
                    start=0
                    while probe and len(positions)<4:
                        pos=markup.find(probe,start)
                        if pos<0:break
                        positions.append(pos);start=pos+len(probe)
                for pos in positions:
                    chunk=markup[max(0,pos-4500):min(len(markup),pos+4500)]
                    for imgscore,img in image_urls(chunk,final):
                        total=linkscore*10+imgscore
                        if best is None or total>best[0]:
                            best=(total,img,event_url,final)
        if best:
            _,img,event_url,ref=best
            if verify(img,ref) or any(x in img.lower() for x in SIGNALS):
                e["image_url"]=img
                e["image_source"]=event_url
                e["image_publishable"]=True
                if not e.get("ticket_url"):e["ticket_url"]=event_url
                recovered+=1
                print("RECOVERED",title,img)
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("recovered",recovered)
    return 0

if __name__=="__main__":raise SystemExit(main())

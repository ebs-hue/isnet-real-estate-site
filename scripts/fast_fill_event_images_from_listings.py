#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, json, re, ssl, time, unicodedata
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit, urlunsplit, parse_qs
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
EVENT_ROOT=ROOT/"events-preview"/"ashdod"
DATA=EVENT_ROOT/"data"/"events.json"
REPORT=EVENT_ROOT/"data"/"listing-image-fill-report.json"
OUT=EVENT_ROOT/"assets"/"events"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
BAD=("logo","favicon","facebook_oauth","google_oauth","microsoft_oauth","artistshadow","eventnew.jpg","placeholder","no_pic","no-pic","default","sprite","spinner","languages/")
TIMEOUT=18

def norm(s):
    s=html.unescape(s or "")
    s=unicodedata.normalize("NFKC",s).replace("־","-").replace("–","-").replace("—","-")
    s=re.sub(r"[\u0591-\u05C7]","",s)
    return re.sub(r"\s+"," ",re.sub(r"[^0-9A-Za-zא-ת]+"," ",s.lower())).strip()

def safe_url(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))

def host(url): return (urlsplit(url).hostname or "").lower()

def fetch(url,ref=None):
    req=Request(safe_url(url),headers={"User-Agent":UA,"Accept-Language":"he-IL,he;q=.9,en;q=.7","Referer":safe_url(ref or url)})
    with urlopen(req,timeout=TIMEOUT,context=ssl.create_default_context()) as r:
        return r.read(),(r.headers.get("Content-Type") or "").lower(),r.geturl()

def get_html(url):
    raw,ctype,final=fetch(url)
    m=re.search(r"charset=([\w-]+)",ctype); enc=m.group(1) if m else "utf-8"
    try:return raw.decode(enc,errors="replace"),final
    except LookupError:return raw.decode("utf-8",errors="replace"),final

def bad_image(u):
    low=html.unescape(u or "").lower()
    return not low or any(x in low for x in BAD)

def image_urls(chunk,base):
    decoded=html.unescape(chunk)
    out=[]
    pats=(
      r'''https?://[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
      r'''//[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
      r'''/[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
      r'''url\(([^)]+\.(?:jpe?g|png|webp|gif)(?:\?[^)]*)?)\)'''
    )
    for pat in pats:
        for m in re.finditer(pat,decoded,re.I):
            raw=m.group(1) if m.lastindex else m.group(0)
            u=urljoin(base,raw.strip().strip("'\""))
            if not bad_image(u): out.append((m.start(),u))
    return out

def needles(e):
    vals=[]
    title=e.get("title") or ""
    if title: vals += [title,html.escape(title,quote=False)]
    ticket=e.get("ticket_url") or ""
    if ticket:
        q=parse_qs(urlsplit(ticket).query)
        if q.get("id"):
            i=q["id"][0]; vals += ["id="+i,"id%3D"+i]
        path=urlsplit(ticket).path
        if path: vals += [path,html.escape(path,quote=True)]
    return sorted(set(v for v in vals if v),key=len,reverse=True)

def score_candidates(e,markup,base):
    poss=[]
    # Prefer stable event id/path, then exact title.
    for needle in needles(e):
        start=0; local=[]
        while True:
            p=markup.find(needle,start)
            if p<0: break
            local.append(p); start=p+max(1,len(needle))
            if len(local)>=8: break
        if local:
            poss=local
            if needle.startswith("id=") or "/?" in needle or needle.startswith("/"): break
    if not poss:return []
    scores={}
    for pos in poss:
        lo=max(0,pos-8500);hi=min(len(markup),pos+8500)
        for rel,u in image_urls(markup[lo:hi],base):
            absolute=lo+rel; dist=abs(absolute-pos); low=u.lower()
            score=max(0,100-dist/100)
            if "/uploads/thumbs/" in low:score+=130
            elif "/uploads/" in low:score+=100
            if "/caps/" in low:score+=100
            if "livenew_" in low or "updateartistimage" in low:score+=95
            if any(x in low for x in ("event","poster","banner","artist")):score+=20
            if "smarticket.co.il" in host(base) and "smarticket" in host(u):score+=20
            scores[u]=max(score,scores.get(u,-999))
    return sorted(((s,u) for u,s in scores.items()),reverse=True)

def download_image(url,ref):
    raw,ctype,_=fetch(url,ref)
    if len(raw)<1200:raise ValueError("small")
    sig=raw[:16]
    if not (ctype.startswith("image/") or sig.startswith(b"\xff\xd8\xff") or sig.startswith(b"\x89PNG") or (sig.startswith(b"RIFF") and b"WEBP" in sig) or sig.startswith(b"GIF8")):
        raise ValueError("not image")
    p=urlsplit(url).path.lower()
    if p.endswith((".jpg",".jpeg")):ext=".jpg"
    elif p.endswith(".png"):ext=".png"
    elif p.endswith(".webp"):ext=".webp"
    elif p.endswith(".gif"):ext=".gif"
    else:ext={"image/png":".png","image/webp":".webp","image/gif":".gif"}.get(ctype.split(";")[0],".jpg")
    OUT.mkdir(parents=True,exist_ok=True)
    name=hashlib.sha256(url.encode()).hexdigest()[:22]+ext
    (OUT/name).write_bytes(raw)
    return "assets/events/"+name

def main():
    data=json.loads(DATA.read_text(encoding="utf-8"));events=data.get("events") or []
    roots=[]
    for e in events:
        if e.get("image_verified") is True:continue
        for s in e.get("sources") or []:
            u=s.get("url") or ""
            if not u:continue
            roots.append(u)
            if "smarticket.co.il" in host(u):roots.append(u.rstrip("/")+"/iframe")
    roots=list(dict.fromkeys(roots))
    pages={}
    for root in roots:
        try:
            pages[root]=get_html(root)
            print("SOURCE",root,"OK",len(pages[root][0]))
        except Exception as ex:
            print("SOURCE",root,"FAIL",type(ex).__name__)
            pages[root]=None

    byid={e["event_id"]:e for e in events}
    options={}
    for e in events:
        if e.get("image_verified") is True:continue
        rows=[]
        allowed_roots=set()
        for s in e.get("sources") or []:
            u=s.get("url") or ""
            if not u:continue
            allowed_roots.add(u)
            if "smarticket.co.il" in host(u):allowed_roots.add(u.rstrip("/")+"/iframe")
        for root in allowed_roots:
            loaded=pages.get(root)
            if not loaded:continue
            markup,final=loaded
            for score,u in score_candidates(e,markup,final)[:10]:
                if score>=65: rows.append((score,u,final))
        if rows:
            best={}
            for row in rows:
                if row[1] not in best or row[0]>best[row[1]][0]:best[row[1]]=row
            options[e["event_id"]]=sorted(best.values(),reverse=True)

    # Images near multiple unrelated event cards are generic page artwork; reject.
    usage=defaultdict(set)
    for eid,rows in options.items():
        for _,u,_ in rows[:5]: usage[u].add(norm(byid[eid].get("title")))
    unsafe={u for u,titles in usage.items() if len(titles)>1}

    stats=Counter();new=[];accepted_title={}
    for e in events:
        if e.get("image_verified") is True:
            accepted_title[norm(e.get("title"))]=e
            continue
        rows=options.get(e["event_id"]) or []
        chosen=next((r for r in rows if r[1] not in unsafe),None)
        if not chosen:continue
        score,u,ref=chosen
        try:local=download_image(u,ref)
        except Exception as ex:
            stats["download_failed"]+=1;continue
        e.update({
          "image_url":local,"image_origin_url":u,"image_source":ref,
          "image_credit":e.get("image_credit") or "צילום או כרזה: אתר המארגן הרשמי",
          "image_publishable":True,"image_verified":True,
          "image_rights_status":"verified_official_source",
          "image_strategy":"source_listing_card",
          "thumbnail_ready":False,"thumbnail_url":None
        })
        accepted_title[norm(e.get("title"))]=e
        stats["accepted"]+=1
        new.append({"event_id":e["event_id"],"title":e.get("title"),"image":u,"source":ref,"score":round(score,1)})
        print("FILLED",e.get("title"),u)

    # Repeated dates of the same production should share the same official artwork.
    for e in events:
        if e.get("image_verified") is True:continue
        src=accepted_title.get(norm(e.get("title")))
        if not src:continue
        for k in ("image_url","image_origin_url","image_source","image_credit"):
            e[k]=src.get(k)
        e.update({"image_publishable":True,"image_verified":True,"image_rights_status":"verified_official_source","image_strategy":"same_production_reuse","thumbnail_ready":False,"thumbnail_url":None})
        stats["same_title_reuse"]+=1
        new.append({"event_id":e["event_id"],"title":e.get("title"),"image":e.get("image_origin_url"),"source":e.get("image_source"),"score":"reuse"})

    missing=[e for e in events if e.get("image_verified") is not True]
    report={
      "generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
      "total_events":len(events),"verified_images":len(events)-len(missing),"still_missing":len(missing),
      "stats":dict(stats),"newly_filled":new,
      "missing":[{"event_id":e.get("event_id"),"title":e.get("title"),"category":e.get("category"),"ticket_url":e.get("ticket_url")} for e in missing]
    }
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SUMMARY",json.dumps({k:v for k,v in report.items() if k not in ("newly_filled","missing")},ensure_ascii=False))
    return 0
if __name__=="__main__":raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, json, re, ssl, time, unicodedata
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, urlsplit, urlunsplit, parse_qs
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
EVENT_ROOT=ROOT/"events-preview"/"ashdod"
DATA=EVENT_ROOT/"data"/"events.json"
REPORT=EVENT_ROOT/"data"/"listing-image-fill-report.json"
OUT=EVENT_ROOT/"assets"/"events"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
BAD=("logo","favicon","facebook_oauth","google_oauth","microsoft_oauth","artistshadow","eventnew.jpg","placeholder","no_pic","no-pic","default","sprite","spinner","languages/")
SIGNALS=("/uploads/thumbs/","/uploads/","/caps/","livenew_","updateartistimage","/events/","/event/")
TIMEOUT=25

def norm(s):
    s=html.unescape(s or "")
    s=unicodedata.normalize("NFKC",s)
    s=s.replace("־","-").replace("–","-").replace("—","-")
    s=re.sub(r"[\u0591-\u05C7]","",s)
    return re.sub(r"\s+"," ",re.sub(r"[^0-9A-Za-zא-ת]+"," ",s.lower())).strip()

def safe_url(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))

def host(url): return (urlsplit(url).hostname or "").lower()

def fetch(url,referer=None,limit=None):
    headers={"User-Agent":UA,"Accept-Language":"he-IL,he;q=.9,en;q=.7","Referer":safe_url(referer or url)}
    if limit: headers["Range"]=f"bytes=0-{limit-1}"
    with urlopen(Request(safe_url(url),headers=headers),timeout=TIMEOUT,context=ssl.create_default_context()) as r:
        return r.read(limit or -1),(r.headers.get("Content-Type") or "").lower(),r.geturl()

def get_html(url):
    raw,ctype,final=fetch(url)
    m=re.search(r"charset=([\w-]+)",ctype)
    enc=m.group(1) if m else "utf-8"
    try: text=raw.decode(enc,errors="replace")
    except LookupError: text=raw.decode("utf-8",errors="replace")
    return text,final

def bad_image(url):
    low=html.unescape(url or "").lower()
    return not low or any(x in low for x in BAD)

def verify_image(url,ref):
    if bad_image(url): return False
    try:
        raw,ctype,_=fetch(url,ref,180000)
        if ctype.startswith("image/"): return len(raw)>1200
        return len(raw)>1200 and (
            raw.startswith(b"\xff\xd8\xff") or
            raw.startswith(b"\x89PNG\r\n\x1a\n") or
            (raw.startswith(b"RIFF") and b"WEBP" in raw[:16]) or
            raw.startswith((b"GIF87a",b"GIF89a"))
        )
    except Exception:
        return False

def raw_image_urls(chunk,base):
    decoded=html.unescape(chunk)
    found=[]
    patterns=(
      r'''https?://[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
      r'''//[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
      r'''/[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
      r'''url\(([^)]+\.(?:jpe?g|png|webp|gif)(?:\?[^)]*)?)\)'''
    )
    for pat in patterns:
        for m in re.finditer(pat,decoded,re.I):
            raw=m.group(1) if m.lastindex else m.group(0)
            u=urljoin(base,raw.strip().strip("'\""))
            if bad_image(u): continue
            found.append((m.start(),u))
    return found

def source_pages(event):
    out=[]
    seen=set()
    for s in event.get("sources") or []:
        u=s.get("url") or ""
        if not u: continue
        for cand in (u, u.rstrip("/")+"/iframe" if "smarticket.co.il" in host(u) else None):
            if cand and cand not in seen:
                seen.add(cand); out.append(cand)
    return out

def event_needles(event):
    needles=[]
    title=event.get("title") or ""
    if title: needles += [title, html.escape(title,quote=False)]
    ticket=event.get("ticket_url") or ""
    if ticket:
        q=parse_qs(urlsplit(ticket).query)
        if q.get("id"):
            eid=q["id"][0]
            needles += ["id="+eid, "id%3D"+eid]
        path=urlsplit(ticket).path
        if path:
            needles += [path, html.escape(path,quote=True)]
    # exact phrases first, longest first
    return sorted({x for x in needles if x},key=len,reverse=True)

def listing_candidates(event,markup,base):
    positions=[]
    for needle in event_needles(event):
        start=0
        while True:
            pos=markup.find(needle,start)
            if pos<0: break
            positions.append(pos); start=pos+max(1,len(needle))
            if len(positions)>=12: break
        if positions: break
    if not positions:
        return []
    scored={}
    for pos in positions[:12]:
        lo=max(0,pos-7000); hi=min(len(markup),pos+7000)
        chunk=markup[lo:hi]
        for rel,u in raw_image_urls(chunk,base):
            absolute=lo+rel
            dist=abs(absolute-pos)
            low=u.lower()
            score=max(0,100-dist/90)
            if "/uploads/thumbs/" in low: score+=90
            elif "/uploads/" in low: score+=70
            if "/caps/" in low: score+=65
            if "livenew_" in low or "updateartistimage" in low: score+=65
            if host(base) in ("ashdod.smarticket.co.il","mishkan-ashdod.smarticket.co.il") and "smarticket" in host(u): score+=20
            prev=scored.get(u)
            if prev is None or score>prev: scored[u]=score
    return sorted(((s,u) for u,s in scored.items()),reverse=True)

def direct_page_candidates(markup,base):
    scored={}
    decoded=html.unescape(markup)
    meta_pats=(
        r'''<(?:meta)[^>]+(?:property|name)=["'](?:og:image|twitter:image|twitter:image:src)["'][^>]+content=["']([^"']+)''',
        r'''<(?:meta)[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["'](?:og:image|twitter:image|twitter:image:src)["']'''
    )
    for pat in meta_pats:
        for m in re.finditer(pat,decoded,re.I):
            u=urljoin(base,m.group(1))
            if not bad_image(u): scored[u]=max(scored.get(u,0),180)
    for _,u in raw_image_urls(decoded,base):
        low=u.lower(); score=30
        if "/uploads/thumbs/" in low: score+=70
        elif "/uploads/" in low: score+=60
        if "/caps/" in low or "livenew_" in low or "updateartistimage" in low: score+=60
        scored[u]=max(scored.get(u,0),score)
    return sorted(((s,u) for u,s in scored.items()),reverse=True)

def cache_image(url,ref):
    raw,ctype,_=fetch(url,ref)
    if len(raw)<1200: raise ValueError("small image")
    path=urlsplit(url).path.lower()
    if path.endswith((".jpg",".jpeg")): ext=".jpg"
    elif path.endswith(".png"): ext=".png"
    elif path.endswith(".webp"): ext=".webp"
    elif path.endswith(".gif"): ext=".gif"
    else:
        ext={"image/png":".png","image/webp":".webp","image/gif":".gif"}.get(ctype.split(";")[0],".jpg")
    OUT.mkdir(parents=True,exist_ok=True)
    name=hashlib.sha256(url.encode()).hexdigest()[:22]+ext
    (OUT/name).write_bytes(raw)
    return "assets/events/"+name

def main():
    data=json.loads(DATA.read_text(encoding="utf-8"))
    events=data.get("events") or []
    html_cache={}
    proposed={}
    diagnostics={}

    # First pass: collect the strongest source-page candidate for every missing event.
    for e in events:
        if e.get("image_verified") is True: continue
        options=[]; tried=[]
        ticket=e.get("ticket_url") or ""

        # Direct event page.
        if ticket.startswith(("http://","https://")):
            try:
                if ticket not in html_cache:
                    time.sleep(.08); html_cache[ticket]=get_html(ticket)
                markup,final=html_cache[ticket]
                for score,u in direct_page_candidates(markup,final)[:10]:
                    if score>=80 and verify_image(u,final):
                        options.append((score+30,u,final,"direct_event_page")); break
                tried.append({"page":final,"kind":"direct","candidates":len(direct_page_candidates(markup,final))})
            except Exception as ex:
                tried.append({"page":ticket,"kind":"direct","error":type(ex).__name__})

        # Original source/listing cards. For Smarticket this is often where the poster lives.
        for root in source_pages(e):
            try:
                if root not in html_cache:
                    time.sleep(.08); html_cache[root]=get_html(root)
                markup,final=html_cache[root]
                cs=listing_candidates(e,markup,final)
                tried.append({"page":final,"kind":"listing","top":[{"score":round(s,1),"url":u} for s,u in cs[:3]]})
                for score,u in cs[:8]:
                    if score>=70 and verify_image(u,final):
                        options.append((score,u,final,"source_listing")); break
            except Exception as ex:
                tried.append({"page":root,"kind":"listing","error":type(ex).__name__})

        if options:
            # Keep alternatives. Generic social images sometimes outrank the real card
            # image, so duplicate detection below must be able to fall back.
            best={}
            for row in options:
                score,u,ref,kind=row
                if u not in best or score>best[u][0]: best[u]=row
            proposed[e["event_id"]]=sorted(best.values(),reverse=True,key=lambda x:x[0])
        diagnostics[e["event_id"]]=tried

    # Any candidate image that appears for unrelated productions is unsafe.
    # This catches generic Tickchak/Smarticket social images while still allowing
    # exact-title repeat performances to share artwork.
    usage=defaultdict(list)
    byid={e["event_id"]:e for e in events}
    for eid,rows in proposed.items():
        for _,u,_,_ in rows:
            usage[u].append(eid)
    unsafe_urls=set()
    for u,ids in usage.items():
        titles={norm(byid[i].get("title")) for i in ids}
        if len(titles)>1: unsafe_urls.add(u)

    stats=Counter()
    accepted_by_title={}
    new_rows=[]
    for e in events:
        if e.get("image_verified") is True:
            accepted_by_title[norm(e.get("title"))]=e
            continue
        rows=proposed.get(e["event_id"]) or []
        p=next((row for row in rows if row[1] not in unsafe_urls),None)
        if not p:
            if rows: stats["rejected_duplicate_across_titles"]+=1
            continue
        score,u,ref,kind=p
        try:
            local=cache_image(u,ref)
        except Exception:
            stats["cache_failed"]+=1
            continue
        e["image_origin_url"]=u
        e["image_url"]=local
        e["image_source"]=ref
        e["image_publishable"]=True
        e["image_verified"]=True
        e["image_strategy"]=kind
        e["thumbnail_ready"]=False
        e["thumbnail_url"]=None
        accepted_by_title[norm(e.get("title"))]=e
        stats["accepted"]+=1
        new_rows.append({"event_id":e["event_id"],"title":e.get("title"),"source":ref,"image":u,"strategy":kind,"score":round(score,1)})

    # Exact-title propagation for repeat dates/performances.
    for e in events:
        if e.get("image_verified") is True: continue
        src=accepted_by_title.get(norm(e.get("title")))
        if not src: continue
        for k in ("image_origin_url","image_url","image_source","image_credit"):
            e[k]=src.get(k)
        e["image_publishable"]=True
        e["image_verified"]=True
        e["image_strategy"]="same_production_reuse"
        e["thumbnail_ready"]=False
        e["thumbnail_url"]=None
        stats["reused_same_title"]+=1
        new_rows.append({"event_id":e["event_id"],"title":e.get("title"),"source":e.get("image_source"),"image":e.get("image_origin_url"),"strategy":"same_production_reuse"})

    missing=[e for e in events if e.get("image_verified") is not True]
    report={
      "generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
      "total_events":len(events),
      "verified_images":len(events)-len(missing),
      "still_missing":len(missing),
      "stats":dict(stats),
      "newly_filled":new_rows,
      "missing":[{"event_id":e.get("event_id"),"title":e.get("title"),"category":e.get("category"),"ticket_url":e.get("ticket_url"),"diagnostics":diagnostics.get(e.get("event_id"),[])} for e in missing]
    }
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("missing","newly_filled")},ensure_ascii=False,indent=2))
    for row in new_rows: print("FILLED",row["title"],row["strategy"],row["image"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())

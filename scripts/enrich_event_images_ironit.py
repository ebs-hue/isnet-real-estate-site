#!/usr/bin/env python3
from __future__ import annotations
import difflib, hashlib, html, json, re, ssl, time, unicodedata
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
EVENT_ROOT=ROOT/"events-preview"/"ashdod"
DATA=EVENT_ROOT/"data"/"events.json"
REPORT=EVENT_ROOT/"data"/"ironit-image-report.json"
OUT=EVENT_ROOT/"assets"/"events"
IRONIT="https://www.ironit.org.il/pastime/event/"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"

STOP={"סדנת","סדנא","מופע","הצגה","באשדוד","אשדוד","ייעודי","לגדולות","מהחיים","סדרת","מפגשים","אירוע","של","עם"}

def norm(s):
    s=html.unescape(s or "")
    s=unicodedata.normalize("NFKC",s).replace("־","-").replace("–","-").replace("—","-")
    s=re.sub(r"[\u0591-\u05C7]","",s)
    return re.sub(r"\s+"," ",re.sub(r"[^0-9A-Za-zא-ת]+"," ",s.lower())).strip()

def toks(s):
    return {x for x in norm(s).split() if len(x)>1 and x not in STOP}

def safe_url(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))

def fetch(url,ref=None):
    req=Request(safe_url(url),headers={"User-Agent":UA,"Accept-Language":"he-IL,he;q=.9,en;q=.7","Referer":safe_url(ref or url)})
    with urlopen(req,timeout=25,context=ssl.create_default_context()) as r:
        return r.read(),(r.headers.get("Content-Type") or "").lower(),r.geturl()

def get_html(url):
    raw,ctype,final=fetch(url)
    return raw.decode("utf-8","replace"),final

def strip_tags(s):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s or ""))).strip()

def parse_cards(markup):
    cards=[]
    # Each Ironit event card is one anchor inside div.event. Use the next event marker
    # as a boundary so nested divs do not confuse parsing.
    starts=[m.start() for m in re.finditer(r'<div\s+class=["\']event["\']',markup,re.I)]
    starts.append(len(markup))
    for i in range(len(starts)-1):
        chunk=markup[starts[i]:starts[i+1]]
        hrefm=re.search(r'<a\s+href=["\']([^"\']+)["\']',chunk,re.I)
        bgm=re.search(r'data-bg=["\']([^"\']+)["\']',chunk,re.I)
        if not hrefm or not bgm: continue
        titlem=re.search(r'<p\s+class=["\']title-text["\'][^>]*>(.*?)</p>',chunk,re.I|re.S)
        title=strip_tags(titlem.group(1)) if titlem else ""
        datem=re.search(r'<span\s+class=["\']date["\'][^>]*>([^<]+)',chunk,re.I)
        date=strip_tags(datem.group(1)) if datem else ""
        cards.append({
          "href":html.unescape(hrefm.group(1)),
          "image":html.unescape(bgm.group(1)),
          "title":title,
          "date":date,
        })
    return cards

def score(event,card):
    a,b=norm(event.get("title")),norm(card["title"])
    ta,tb=toks(event.get("title")),toks(card["title"])
    seq=difflib.SequenceMatcher(None,a,b).ratio() if a and b else 0
    overlap=len(ta&tb)/max(1,len(ta))
    reverse=len(ta&tb)/max(1,len(tb))
    contains=1 if (a and b and (a in b or b in a)) else 0
    s=max(seq,overlap,contains)*60 + reverse*25
    # Exact event date is very strong supporting evidence.
    sd=str(event.get("start_date") or "")
    if sd and re.fullmatch(r"\d{4}-\d{2}-\d{2}",sd):
        y,m,d=sd.split("-")
        iron=f"{d}.{m}.{y}"
        if iron==card.get("date"): s+=35
    return s,seq,overlap,reverse

def cache_image(url,ref):
    raw,ctype,_=fetch(url,ref)
    if len(raw)<1500: raise ValueError("small")
    p=urlsplit(url).path.lower()
    if p.endswith((".jpg",".jpeg")):ext=".jpg"
    elif p.endswith(".png"):ext=".png"
    elif p.endswith(".webp"):ext=".webp"
    elif p.endswith(".gif"):ext=".gif"
    else: ext={"image/png":".png","image/webp":".webp","image/gif":".gif"}.get(ctype.split(";")[0],".jpg")
    OUT.mkdir(parents=True,exist_ok=True)
    name=hashlib.sha256(url.encode()).hexdigest()[:22]+ext
    (OUT/name).write_bytes(raw)
    return "assets/events/"+name

def main():
    data=json.loads(DATA.read_text(encoding="utf-8"))
    markup,final=get_html(IRONIT)
    cards=parse_cards(markup)
    print("IRONIT_CARDS",len(cards))
    filled=[]; ambiguous=[]

    for e in data.get("events") or []:
        if e.get("image_verified") is True: continue
        ranked=[]
        for c in cards:
            s,seq,ov,rev=score(e,c)
            ranked.append((s,seq,ov,rev,c))
        ranked.sort(key=lambda x:x[0],reverse=True)
        if not ranked:continue
        best=ranked[0]
        second=ranked[1] if len(ranked)>1 else None
        s,seq,ov,rev,c=best
        gap=s-(second[0] if second else 0)

        # Require strong textual identity or medium identity plus exact-date support.
        date_match=False
        sd=str(e.get("start_date") or "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}",sd):
            y,m,d=sd.split("-"); date_match=(f"{d}.{m}.{y}"==c.get("date"))
        strong=(ov>=0.62 and rev>=0.45) or seq>=0.72 or norm(e.get("title")) in norm(c["title"]) or norm(c["title"]) in norm(e.get("title"))
        medium=(ov>=0.42 and rev>=0.38 and date_match)

        if not (strong or medium) or (gap<5 and not date_match):
            ambiguous.append({
              "event_id":e.get("event_id"),"title":e.get("title"),
              "best_title":c.get("title"),"score":round(s,1),"gap":round(gap,1),"date_match":date_match
            })
            continue
        try:
            local=cache_image(c["image"],c["href"])
        except Exception as ex:
            ambiguous.append({"event_id":e.get("event_id"),"title":e.get("title"),"error":type(ex).__name__})
            continue
        e.update({
          "image_url":local,
          "image_origin_url":c["image"],
          "image_source":c["href"],
          "image_credit":"החברה העירונית לתרבות הפנאי אשדוד",
          "image_publishable":True,
          "image_verified":True,
          "image_strategy":"ironit_official_event_card",
          "thumbnail_ready":False,
          "thumbnail_url":None
        })
        filled.append({"event_id":e.get("event_id"),"title":e.get("title"),"matched":c["title"],"image":c["image"],"score":round(s,1),"date_match":date_match})
        print("FILLED",e.get("title"),"==",c["title"],c["image"])

    # Reuse exact-title production artwork across repeated dates.
    bytitle={}
    for e in data.get("events") or []:
        if e.get("image_verified") is True:bytitle[norm(e.get("title"))]=e
    for e in data.get("events") or []:
        if e.get("image_verified") is True:continue
        src=bytitle.get(norm(e.get("title")))
        if not src:continue
        for k in ("image_url","image_origin_url","image_source","image_credit"):
            e[k]=src.get(k)
        e.update({"image_publishable":True,"image_verified":True,"image_strategy":"same_production_reuse","thumbnail_ready":False,"thumbnail_url":None})
        filled.append({"event_id":e.get("event_id"),"title":e.get("title"),"matched":"same-title reuse","image":e.get("image_origin_url")})

    missing=[e for e in data.get("events") or [] if e.get("image_verified") is not True]
    report={"generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"ironit_cards":len(cards),"filled":filled,"filled_count":len(filled),"verified_total":len(data.get("events") or [])-len(missing),"missing_count":len(missing),"ambiguous":ambiguous,"missing":[{"event_id":e.get("event_id"),"title":e.get("title")} for e in missing]}
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SUMMARY",json.dumps({k:v for k,v in report.items() if k not in ("filled","ambiguous","missing")},ensure_ascii=False))
    return 0

if __name__=="__main__":raise SystemExit(main())

#!/usr/bin/env python3
import hashlib, json, ssl
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview"/"ashdod"/"data"/"events.json"
OUT=ROOT/"events-preview"/"ashdod"/"assets"/"events"
ALLOWED={"static.tickchak.co.il","ashdod.smarticket.co.il","mishkan-ashdod.smarticket.co.il","static.smarticket.co.il"}
UA="Mozilla/5.0 Chrome/154 Safari/537.36"

def allowed(url):
    return (urlsplit(url).hostname or "").lower() in ALLOWED

def safe(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))

def ext(url,ctype):
    path=urlsplit(url).path.lower()
    if path.endswith((".jpg",".jpeg")):return ".jpg"
    if path.endswith(".png"):return ".png"
    if path.endswith(".webp"):return ".webp"
    if path.endswith(".gif"):return ".gif"
    return {"image/png":".png","image/webp":".webp","image/gif":".gif"}.get((ctype or "").split(";")[0],".jpg")

def main():
    data=json.loads(DATA.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True,exist_ok=True)
    seen={};ok=0;fail=0
    for e in data.get("events",[]):
        u=e.get("image_url") or ""
        if not (e.get("image_publishable") is True and u.startswith("https://") and allowed(u)):
            continue
        if u in seen:
            e["image_origin_url"]=u;e["image_url"]=seen[u];ok+=1;continue
        ref=e.get("image_source") or e.get("ticket_url") or u
        if not allowed(ref):ref=u
        try:
            req=Request(safe(u),headers={"User-Agent":UA,"Referer":safe(ref),"Accept":"image/*"})
            with urlopen(req,timeout=25,context=ssl.create_default_context()) as r:
                ctype=(r.headers.get("Content-Type") or "").lower()
                raw=r.read(12*1024*1024)
            if len(raw)<800 or not (ctype.startswith("image/") or raw.startswith((b"\xff\xd8\xff",b"\x89PNG",b"RIFF",b"GIF8"))):
                raise ValueError("invalid image")
            name=hashlib.sha256(u.encode()).hexdigest()[:20]+ext(u,ctype)
            (OUT/name).write_bytes(raw)
            rel="assets/events/"+name
            seen[u]=rel;e["image_origin_url"]=u;e["image_url"]=rel;ok+=1
        except Exception:
            fail+=1
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"cached={ok} failed={fail} unique={len(seen)}")
if __name__=="__main__":main()

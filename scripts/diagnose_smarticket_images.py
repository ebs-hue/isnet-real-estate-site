#!/usr/bin/env python3
import html,re,ssl
from urllib.request import Request,urlopen
from urllib.parse import quote,urlsplit,urlunsplit

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
tests=[
 ("https://mishkan-ashdod.smarticket.co.il/","8214","מיקה שלי"),
 ("https://mishkan-ashdod.smarticket.co.il/","8059","היפהפיה הנרדמת"),
 ("https://mishkan-ashdod.smarticket.co.il/","8140","החולה ההודי"),
 ("https://ashdod.smarticket.co.il/","17635","הענק הכי גנדרן בעולם"),
 ("https://ashdod.smarticket.co.il/","17235","מפגשי קריאה"),
]
def safe(u):
 p=urlsplit(u);return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))
def get(u):
 r=urlopen(Request(safe(u),headers={"User-Agent":UA}),timeout=25,context=ssl.create_default_context())
 return r.read().decode("utf-8","replace")
def urls(chunk):
 dec=html.unescape(chunk)
 pats=[
  r'https?://[^"\'<>\s\\]+',
  r'//[^"\'<>\s\\]+',
  r'/uploads/[^"\'<>\s\\]+',
  r'(?:src|data-src|data-image|data-original|background-image|backgroundImage)\s*[:=]\s*["\']([^"\']+)'
 ]
 out=[]
 for pat in pats:
  for m in re.finditer(pat,dec,re.I):
   x=m.group(1) if m.lastindex else m.group(0)
   if any(k in x.lower() for k in ("upload","thumb","image","jpg","jpeg","png","webp","gif")):
    out.append((m.start(),x[:500]))
 return out
for base,eid,title in tests:
 src=get(base)
 print("\n===",title,eid,base,"LEN",len(src))
 positions=[]
 for needle in ("id="+eid,title):
  p=src.find(needle)
  print("NEEDLE",repr(needle),"POS",p)
  if p>=0:positions.append(p)
 if not positions:continue
 p=positions[0]
 for radius in (3000,10000,25000):
  lo=max(0,p-radius);hi=min(len(src),p+radius);chunk=src[lo:hi]
  us=urls(chunk)
  print("RADIUS",radius,"URLS",len(us))
  for rel,u in sorted(us,key=lambda x:abs((lo+x[0])-p))[:15]:
   print(" ",(lo+rel)-p,u)
  if us:break
 print("SNIPPET",re.sub(r"\s+"," ",html.unescape(src[max(0,p-1200):p+1200]))[:2400])

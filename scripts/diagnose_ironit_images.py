#!/usr/bin/env python3
import html,re,ssl
from urllib.request import Request,urlopen
from urllib.parse import quote,urlsplit,urlunsplit
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
url="https://www.ironit.org.il/pastime/event/"
def safe(u):
 p=urlsplit(u);return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))
r=urlopen(Request(safe(url),headers={"User-Agent":UA}),timeout=25,context=ssl.create_default_context())
src=r.read().decode("utf-8","replace")
print("LEN",len(src))
for title in ("מפגשי קריאה","הענק הכי גנדרן בעולם","מועדון הקוראות הרומנטיות","קורס גישור בסיסי","נמרולוגיה על בסיס קבלה","סדנת חופשה בקליק"):
 p=src.find(title);print("\nTITLE",title,"POS",p)
 if p<0:continue
 lo=max(0,p-7000);hi=min(len(src),p+7000);chunk=html.unescape(src[lo:hi])
 pats=(r'https?://[^"\'<>\s\\]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"\'<>\s\\]*)?',r'/[^"\'<>\s\\]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"\'<>\s\\]*)?')
 out=[]
 for pat in pats:
  for m in re.finditer(pat,chunk,re.I):
   u=m.group(0)
   if not any(x in u.lower() for x in ("logo","icon","favicon","sprite")):
    out.append((lo+m.start()-p,u))
 for row in sorted(out,key=lambda x:abs(x[0]))[:20]:print(row)
 print("SNIP",re.sub(r"\s+"," ",chunk[6000:8000])[:2000])

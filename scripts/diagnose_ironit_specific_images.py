#!/usr/bin/env python3
import html,re,ssl
from urllib.request import Request,urlopen
from urllib.parse import quote,urlsplit,urlunsplit

URL="https://www.ironit.org.il/pastime/event/"
UA="Mozilla/5.0 Chrome/154 Safari/537.36"
queries=[
 "מפגשי קריאה","כוורת","החיפושיות","עיצוב אורח חיים בריא","נמרולוגיה",
 "חלוקי נחל","תליונים","קנווה","חופשה בקליק","גישור","אסתטיקה"
]
def safe(u):
 p=urlsplit(u);return urlunsplit((p.scheme,p.netloc,quote(p.path,safe="/%:@-._~!$&()*+,;="),quote(p.query,safe="=&%:@/?-._~!$()*+,;"),""))
src=urlopen(Request(safe(URL),headers={"User-Agent":UA}),timeout=25,context=ssl.create_default_context()).read().decode("utf-8","replace")
starts=[m.start() for m in re.finditer(r'<div\s+class=["\']event["\']',src,re.I)]+[len(src)]
cards=[]
for i in range(len(starts)-1):
 ch=src[starts[i]:starts[i+1]]
 tm=re.search(r'<p\s+class=["\']title-text["\'][^>]*>(.*?)</p>',ch,re.I|re.S)
 bg=re.search(r'data-bg=["\']([^"\']+)["\']',ch,re.I)
 hr=re.search(r'<a\s+href=["\']([^"\']+)["\']',ch,re.I)
 if tm and bg:
  title=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",tm.group(1)))).strip()
  cards.append((title,html.unescape(bg.group(1)),html.unescape(hr.group(1)) if hr else ""))
for q in queries:
 print("\n==",q)
 hits=[c for c in cards if q in c[0]]
 for c in hits[:20]: print("CARD",c[0],"|",c[1],"|",c[2])

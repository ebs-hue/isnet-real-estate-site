#!/usr/bin/env python3
"""Import dated city events from national-board detail pages into city datasets."""
import hashlib,json,re
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DISC=ROOT/"events-preview/admin/data/national-events-discovery.json"
CITIES={"ashdod":"אשדוד","rishon-lezion":"ראשון לציון"}
HEADERS={"User-Agent":"ISNET-Events/1.0","Accept-Language":"he-IL,he;q=0.9"}
def norm(x):return re.sub(r"\s+"," ",str(x or "")).strip()
def event_nodes(value):
    if isinstance(value,list):
        for v in value:yield from event_nodes(v)
    elif isinstance(value,dict):
        types=value.get("@type",[])
        if isinstance(types,str):types=[types]
        if any(str(t).split("/")[-1]=="Event" or str(t).endswith("Event") for t in types):yield value
        for key in ("@graph","mainEntity","itemListElement"):
            if key in value:yield from event_nodes(value[key])
def string(v):
    if isinstance(v,list):return string(v[0]) if v else ""
    if isinstance(v,dict):return norm(v.get("name") or v.get("url") or "")
    return norm(v)
def extract(html,url,city):
    soup=BeautifulSoup(html,"html.parser")
    records=[]
    for tag in soup.select('script[type="application/ld+json"]'):
        try:raw=json.loads(tag.string or tag.get_text())
        except (ValueError,TypeError):continue
        for e in event_nodes(raw):
            title=string(e.get("name"));start=string(e.get("startDate"))
            try:
                dt=datetime.fromisoformat(start.replace("Z","+00:00"))
                day=dt.date().isoformat();clock=dt.strftime("%H:%M")
            except ValueError:continue
            if day < date.today().isoformat():continue
            location=e.get("location") or {}
            if isinstance(location,list):location=location[0] if location else {}
            if isinstance(location,str):location={"name":location}
            address=location.get("address") or {} if isinstance(location,dict) else {}
            addr=string(address) if isinstance(address,str) else string(address.get("addressLocality")) if isinstance(address,dict) else ""
            venue=string(location.get("name")) if isinstance(location,dict) else ""
            context=" ".join([venue,addr,string(e.get("description")),title])
            if city not in context and not (city=="ראשון לציון" and "ראשל" in context):continue
            img=e.get("image");img=img[0] if isinstance(img,list) and img else img
            if isinstance(img,dict):img=img.get("url") or img.get("contentUrl")
            image=string(img)
            if not image.startswith("https://"):image=None
            desc=BeautifulSoup(string(e.get("description")),"html.parser").get_text(" ",strip=True)
            if not title or not venue:continue
            records.append(dict(title=title,start_date=day,start_time=clock,venue=venue,description=desc,image_url=image,source_url=url))
    return records

VENUES={
 "אשדוד":["המשכן לאמנויות הבמה אשדוד","בית יד לבנים אשדוד","מונארט מרכז תרבות אשדוד","מתנ\"ס דיונה, אשדוד","סינמה סיטי אשדוד","הוט סינמה אשדוד","נאפו בר אשדוד","אמפי אשדוד"],
 "ראשון לציון":["היכל התרבות ראשון לציון","אמפי MAX ראשון לציון","אמפי לייב פארק ראשון לציון","בית העם ראשון לציון","מועדון התדר ראשון לציון","סינמה סיטי ראשון לציון","יס פלאנט ראשון לציון","ראשון לציון"]
}
def listing_rows(html,url,city):
    """Read visible date/time/title/venue rows, not just JSON-LD metadata."""
    soup=BeautifulSoup(html,"html.parser")
    for x in soup(["script","style","nav","footer"]):x.decompose()
    raw=soup.get_text(" ",strip=True)
    raw=re.sub(r"\\s+"," ",raw)
    # Mevalim's event list presents day.month followed by weekday, time, title, venue.
    pattern=r"(?<!\\d)(\\d{1,2})\\.(\\d{1,2})\\s+(?:יום\\s+)?(?:ראשון|שני|שלישי|רביעי|חמישי|שישי|שבת)\\s+(\\d{1,2}:\\d{2})\\s*\\|?\\s*"
    hits=list(re.finditer(pattern,raw))
    output=[]
    for i,m in enumerate(hits):
        part=raw[m.end():(hits[i+1].start() if i+1<len(hits) else m.end()+380)]
        venue=next((v for v in sorted(VENUES[city],key=len,reverse=True) if v in part),None)
        if not venue:continue
        title=norm(part.split(venue,1)[0].strip(" |"))
        title=re.sub(r"\\s*(?:לרכישה|לפרטים|הכרטיסים אזלו).*$","",title).strip()
        if not (3<=len(title)<=170):continue
        month=int(m.group(2));day=int(m.group(1));year=date.today().year
        try:
            dt=date(year,month,day)
            if dt<date.today():dt=date(year+1,month,day)
        except ValueError:continue
        output.append(dict(title=title,start_date=dt.isoformat(),start_time=m.group(3),venue=venue,description="",image_url=None,source_url=url))
    return output

def main():
    d=json.loads(DISC.read_text(encoding="utf-8"))
    session=requests.Session();session.headers.update(HEADERS)
    report={"generated_at":datetime.now(timezone.utc).isoformat(),"sources":{},"cities":{}}
    for slug,label in CITIES.items():
        path=ROOT/"events-preview"/slug/"data/events.json"
        data=json.loads(path.read_text(encoding="utf-8"));events=data["events"]
        seen={(e.get("title"),e.get("start_date"),e.get("start_time"),e.get("venue")) for e in events}
        count=0
        candidates=[{"city_hint":slug,"source_url":"https://www.mevalim.co.il/"+("ashdod" if slug=="ashdod" else "rishon-lezion")+"/","source_id":"mevalim"}]
        candidates += [c for c in d.get("candidates",[]) if c.get("source_id")!="mevalim"]
        for candidate in candidates:
            if candidate.get("city_hint")!=slug:continue
            url=candidate.get("source_url","")
            host=urlparse(url).hostname or ""
            if not host or not url.startswith("https://"):continue
            try:
                response=session.get(url,timeout=15)
                response.raise_for_status()
                if (urlparse(response.url).hostname or "")!=host:continue
                rows=extract(response.text,url,label)\n                if candidate.get("source_id")=="mevalim":rows+=listing_rows(response.text,url,label)
            except (requests.RequestException,ValueError,TypeError):continue
            for row in rows:
                key=tuple(row[k] for k in ("title","start_date","start_time","venue"))
                if key in seen:continue
                seen.add(key)
                eid="auto_"+slug[:2]+"_"+hashlib.sha256(("|".join(key)).encode()).hexdigest()[:20]
                events.append({"event_id":eid,"city":label,"title":row["title"],"description":row["description"] or row["title"],"start_date":row["start_date"],"start_time":row["start_time"],"venue":row["venue"],"category":"other","ticket_url":url,"image_url":row["image_url"],"image_source":url,"image_origin_url":url,"image_publishable":bool(row["image_url"]),"image_verified":bool(row["image_url"]),"image_rights_status":"needs_review","sources":[{"name":candidate.get("source_id"),"url":url,"source_type":"national_board"}],"status":"active","quality_flags":["national_board_import"]})
                count+=1
        if count:
            events.sort(key=lambda e:(e.get("start_date") or "",e.get("start_time") or "",e.get("title") or ""))
            data["generated_at"]=report["generated_at"]
            data.setdefault("stats",{})["events"]=len(events)
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        report["cities"][slug]={"added":count,"total":len(events)}
    (ROOT/"events-preview/admin/data/national-board-import-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()

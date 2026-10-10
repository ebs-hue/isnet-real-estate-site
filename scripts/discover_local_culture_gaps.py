#!/usr/bin/env python3
"""Daily complementary local-culture discovery for active ISNET cities.
Read-only event candidates; national collection remains the first pass.
"""
import json,re,time
from pathlib import Path
from urllib.parse import urljoin,urlparse
from datetime import datetime,timezone
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"events-preview/admin/data/local-culture-gaps-ashdod-rishon.json"
SOURCES=[
 {"city":"ashdod","venue":"דיונה ומרכזים קהילתיים","url":"https://www.ironit.org.il/activity/מוזיקה-תחומים-לארוע/","type":"community_program"},
 {"city":"ashdod","venue":"החברה העירונית לתרבות ופנאי - כולל דיונה, מונארט ומוזיאונים","url":"https://ashdod.smarticket.co.il/","type":"ticket_calendar"},
 {"city":"ashdod","venue":"המשכן, בית יד לבנים ואמפי אשדוד","url":"https://mishkan-ashdod.smarticket.co.il/","type":"ticket_calendar"},
 {"city":"ashdod","venue":"המשכן לאמנויות הבמה","url":"https://www.mishkan-ashdod.co.il/mishkanmob/eventslist.asp","type":"venue_calendar"},
 {"city":"rishon-lezion","venue":"היכל התרבות ומוסדות העיר","url":"https://htrl.co.il/third-calendar/","type":"city_calendar"},
 {"city":"rishon-lezion","venue":"היכל התרבות ראשון לציון","url":"https://htrl.smarticket.co.il/","type":"ticket_calendar"}
]
def clean(s):return re.sub(r"\s+"," ",str(s or "")).strip()
def run():
    results=[];status=[]
    with requests.Session() as session:
      for source in SOURCES:
        try:
          resp=session.get(source["url"],headers={"User-Agent":"ISNET-Events-Research/1.0","Accept-Language":"he-IL,he;q=.9"},timeout=22)
          resp.raise_for_status()
          if (urlparse(resp.url).hostname or "").removeprefix("www.") != (urlparse(source["url"]).hostname or "").removeprefix("www."):
              raise ValueError("unexpected domain redirect")
          soup=BeautifulSoup(resp.text,"html.parser")
          seen=set();count=0
          for a in soup.select("a[href]"):
            url=urljoin(resp.url,a.get("href",""))
            if (urlparse(url).hostname or "").removeprefix("www.") != (urlparse(resp.url).hostname or "").removeprefix("www."):continue
            title=clean(a.get_text(" ",strip=True))
            if not 12<=len(title)<=175:continue
            # Preserve source candidates for gap comparison, never auto-publish vague cards.
            if not any(w in title for w in ("2026","2027","כרטיס","פרטים","הצגה","מופע","סטנד","מוזיקה","הרצאה","סדנ","פסטיבל","ילדים")):continue
            key=(title,url)
            if key in seen:continue
            seen.add(key)
            img=a.find("img")
            results.append({"city":source["city"],"venue_source":source["venue"],
              "title_candidate":title,"source_url":url,
              "image_candidate_url":urljoin(resp.url,img.get("src")) if img and img.get("src") else None,
              "status":"requires_occurrence_date_and_locality_validation"})
            count+=1
            if count>=160:break
          status.append({"source":source["venue"],"city":source["city"],"url":source["url"],"found":count,"error":None})
        except Exception as ex:status.append({"source":source["venue"],"city":source["city"],"url":source["url"],"found":0,"error":type(ex).__name__+": "+str(ex)[:120]})
        time.sleep(.5)
    report={"generated_at":datetime.now(timezone.utc).isoformat(),"sources":status,
      "cities":["ashdod","rishon-lezion"],"local_candidates":results,
      "publication_enabled":False,"cms_modified":False,
      "note":"Follow national board collection; local candidates must be matched to date, city and venue before creating/updating events."}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"sources_checked":len(status),"found":len(results),"errors":sum(bool(x["error"]) for x in status)},ensure_ascii=False))
if __name__=="__main__":run()

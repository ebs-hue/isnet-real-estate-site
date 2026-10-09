#!/usr/bin/env python3
"""Audit event descriptions for reader comprehension without inventing facts."""
import json,re
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
CITIES=("ashdod","rishon-lezion")
BOILERPLATE=("לרכישת כרטיסים","כרטיסים זמינים","מחיר הכרטיס","מחירים","שעת התחלה","משך משוער","בדקו את הפרטים","בעמוד הרכישה","לפרטים נוספים","המשך התהליך","הנחיות")
CATEGORIES={"music":"מוזיקה","theatre":"תיאטרון","standup":"סטנדאפ","kids":"ילדים","lecture":"הרצאה","conference":"כנס","exhibition":"תערוכה","festival":"פסטיבל","community":"קהילה","tour":"טיול","sport":"ספורט","cinema":"קולנוע","food":"אוכל","seniors":"גמלאים"}
def clean(x):return re.sub(r"\s+"," ",str(x or "")).strip()
def audit(e):
    title=clean(e.get("title")); desc=clean(e.get("long_description") or e.get("description") or e.get("short_pitch") or "")
    reasons=[]; questions=[]; score=100
    boiler=sum(x in desc for x in BOILERPLATE)
    if not title or len(title)<8 or title in ("אירוע","מופע","פעילות"):
        reasons.append("כותרת כללית או לא מזהה");questions.append("מה שמו המדויק של האירוע?");score-=25
    if len(desc)<110:
        reasons.append("תיאור קצר מדי להבנת החוויה");questions.append("מה בדיוק קורה באירוע?");score-=30
    if boiler>=2 and len(desc)<400:
        reasons.append("התיאור מתמקד בלוגיסטיקה או כרטיסים ולא בתוכן");questions.append("מה תוכן האירוע מעבר למועד ולמחיר?");score-=30
    category=clean(e.get("category"))
    if not category or category not in CATEGORIES:
        reasons.append("סוג האירוע אינו מסווג באופן ברור");questions.append("האם מדובר בהצגה, הרצאה, הופעה או פעילות אחרת?");score-=15
    audience=clean(e.get("target_audience") or e.get("audience") or e.get("age_group"))
    audience_terms=("לילדים","למשפחות","למבוגרים","לגילאי","לגיל","לנוער","לגמלאים","לנשים","לפעוטות","לכל המשפחה","מתאים ל")
    if not audience and not any(x in title+" "+desc for x in audience_terms):
        reasons.append("לא ברור למי האירוע מיועד");questions.append("מהו קהל היעד והאם קיימת הגבלת גיל?");score-=15
    value_terms=("במהלך","סיפור","מסע","חוו","משתתפ","ללמוד","מופע של","הופעה של","יצירה","מציג","תגלו","להכיר","סדנה","יצפו","נכיר","שירים","מוזיקה","קומדיה","הרצאה על")
    if not any(x in desc for x in value_terms):
        reasons.append("לא מוסבר מה המשתתף יחווה או יקבל");questions.append("למה כדאי להגיע ומה ייחודי באירוע?");score-=20
    if len(desc)>80 and len(re.findall(r"\b(?:ש\"ח|2026|2027|כרטיס|בשעה|דקות)\b",desc))>=4:
        reasons.append("עומס בפרטים טכניים");score-=10
    score=max(0,score)
    return {"event_id":e.get("event_id"),"title":title,"category":category,"score":score,"severity":"critical" if score<45 else "needs_review" if score<75 else "acceptable","reasons":reasons,"questions_for_source":questions,"source_url":e.get("detail_source_url") or (e.get("sources") or [{}])[0].get("url"),"recommendation":"להשלים מידע ממקור האירוע; לא להמציא תוכן" if reasons else "ללא ליקוי בולט בבדיקה אוטומטית"}
def main():
    for city in CITIES:
        src=ROOT/"events-preview"/city/"data/events.json"
        if not src.exists():continue
        events=json.loads(src.read_text(encoding="utf-8")).get("events",[])
        results=[audit(e) for e in events]
        results.sort(key=lambda x:(x["score"],x["title"]))
        report={"generated_at":datetime.now(timezone.utc).isoformat(),"city":city,"method":"heuristic triage; requires human/AI review for semantics","total":len(results),"critical":sum(x["severity"]=="critical" for x in results),"needs_review":sum(x["severity"]=="needs_review" for x in results),"events":results}
        out=ROOT/"events-preview"/"admin"/"data"/f"content-quality-{city}.json"
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2 )+"\n",encoding="utf-8")
        print(city,report["total"],report["critical"],report["needs_review"],out)
if __name__=="__main__":main()

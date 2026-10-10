#!/usr/bin/env python3
"""Read-only subcategory audit and conservative classification suggestions, Ashdod (initial run).

Does NOT touch the event feed, CMS, publication status or photographs.
"""
import json
import re
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"events-preview/ashdod/data/events.json"
TAXONOMY=ROOT/"events-preview/admin/data/taxonomy.json"
REPORT=ROOT/"events-preview/admin/data/subcategory-audit-ashdod.json"

# An exact contextual title pattern is used only to stage suggestions, never to publish them.
RULES={
 "kids":[
  (r"שעת סיפור|סיפור עם|מספר(?:ת)? סיפורים|הקראת סיפור","story-time",0.98),
  (r"סדנ(?:ה|ת) (?:יצירה )?(?:ל)?ילדים|יצירה לילדים","kids-workshops",0.93),
  (r"הצגת ילדים|הצגה לילדים|תיאטרון ילדים|הצגה - Live|הדרדסים ההצגה|חיפזון וזהירון","kids-theatre",0.95),
  (r"מופע ילדים|מופע לכל המשפחה","kids-shows",0.85),
  (r"פעילות לכל המשפחה|פעילות משפחתית","family-activity",0.82)],
 "music":[
  (r"קונצרט|תזמורת|סימפוני|פילהרמוני","concerts",0.96),
  (r"מופע מחווה|מחווה ל","tribute-shows",0.94),
  (r"שירה בציבור","sing-along",0.97),
  (r"קריוקי","karaoke",0.97),
  (r"מופע מחול|להקת מחול|MALEVO","dance-performance",0.95),
  (r"ג'אז|גאז","jazz",0.93)],
 "theatre":[
  (r"מחזמר|תיאטרון מוזיקלי","musical",0.95),
  (r"קומדיה|הצגה קומית","comedy",0.90),
  (r"מונודרמה|הצגת יחיד","one-person-show",0.96)],
 "standup":[(r"סטנדאפ|סטנד אפ|סטנד-אפ","standup",0.97)],
 "community":[(r"ריקודי עם|הרקדה","folk-dancing",0.98),(r"מועדון קוראות|מועדון קריאה","reading-clubs",0.95),
 (r"גדולות מהחיים","women-events",0.90)],
 "seniors":[(r"ריקודי עם|הרקדה|ריקוד","senior-dance",0.91),(r"סיור|טיול","senior-trips",0.86),
 (r"הרצאה","senior-lectures",0.88),(r"סדנה|יצירה","senior-workshops",0.84)],
 "sport":[(r"כדוריד","handball",0.97),(r"כדורעף","volleyball",0.97),
 (r"כדורסל","basketball",0.97),(r"כדורגל","football",0.97),
 (r"גלישה|סאפ|חתירה","water-sports",0.88),
 (r"מ\\.ס\\.? אשדוד","ms-ashdod-home-games",0.90)],
 "exhibition":[(r"סיור מודרך בתערוכ|סיורים מודרכים במוזיאון","guided-exhibition-tour",0.97),
 (r"כניסה לתערוכות|תערוכה במוזיאון","museums-galleries",0.89)],
 "cinema":[(r"סינמה סיטי","cinema-city",0.98),(r"הוט סינמה","hot-cinema",0.98)]
}
def infer(event,valid):
    cat=event.get("category")
    title=str(event.get("title") or "")
    content=" ".join(str(event.get(k) or "") for k in ("short_pitch","event_summary","description","long_description","series_description"))
    # Title evidence outranks incidental words in description.
    for field,weight in ((title,1.0),(content,0.84)):
        matches=[(sub,round(conf*weight,2),pattern) for pattern,sub,conf in RULES.get(cat,[])
                 if sub in valid.get(cat,set()) and re.search(pattern,field,re.I)]
        if matches:
            # Conflicting candidates require a human review, except the more specific title match.
            matches.sort(key=lambda x:x[1],reverse=True)
            return (*matches[0][:2],"title" if weight==1 else "description",len({m[0] for m in matches})>1)
    return None,0.0,None,False

def run():
    events=json.loads(FEED.read_text(encoding="utf-8")).get("events",[])
    taxonomy=json.loads(TAXONOMY.read_text(encoding="utf-8")).get("primary_categories",[])
    valid={g["id"]:{s["id"] for s in g.get("subcategories",[])} for g in taxonomy}
    counts=Counter()
    findings=[]
    for e in events:
        cat=e.get("category"); sub=e.get("subcategory"); title=str(e.get("title") or "")
        if cat not in valid:
            counts["unknown_category"]+=1;continue
        if sub in valid[cat]:
            counts["already_valid"]+=1;continue
        counts["missing_or_invalid"]+=1
        candidate,confidence,evidence,conflict=infer(e,valid)
        if e.get("subcategory_manual_override"):
            candidate,confidence,evidence=None,0.0,"manual_lock"
        if candidate:counts["staged_candidate"]+=1
        else:counts["needs_contextual_review"]+=1
        status="suggestion_only" if candidate else "needs_review"
        if conflict or confidence<0.85:status="needs_review"
        findings.append({"event_id":e.get("event_id"),"title":title,"category":cat,"existing_subcategory":sub,
                         "suggested_subcategory":candidate,"confidence":confidence,"evidence_field":evidence,
                         "conflict":conflict,"status":status})
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({"city":"ashdod","publication_enabled":False,"total":len(events),
                      "counts":dict(counts),"events":findings},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"total":len(events),"counts":dict(counts)},ensure_ascii=False))

if __name__=="__main__":run()

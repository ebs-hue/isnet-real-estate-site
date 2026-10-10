#!/usr/bin/env python3
"""Read-only subcategory audit and conservative classification suggestions, Ashdod (initial run).

Does NOT touch the event feed, CMS, publication status or photographs.
"""
import json
import re
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"events-preview/ashdod/data/events.json"
TAXONOMY=ROOT/"events-preview/admin/data/taxonomy.json"
REPORT=ROOT/"events-preview/admin/data/subcategory-audit-ashdod.json"
DEFINITIONS=ROOT/"events-preview/admin/data/subcategory-definitions.json"

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
 (r"כניסה לתערוכות|תערוכה במוזיאון","museums-galleries",0.97)],
 "cinema":[(r"סינמה סיטי","cinema-city",0.98),(r"הוט סינמה","hot-cinema",0.98)]
}

# More specific activity cues. Organizer/audience are not activity types.
RULES["lecture"]=[
 (r"גמילה מחיתולים|הורות|הורים|חינוך ילדים|התפתחות הילד","parenting-family",0.93),
 (r"בריאות|רפואה|רפואי|מחלה|חולי|טיפול רפואי|תזונה","health-medicine",0.90),
 (r"נפש|פסיכולוג|חוסן|התפתחות אישית|לצמוח מהכאב|העצמה","psychology-growth",0.89),
 (r"היסטוריה|היסטורי|העבר|מורשת","history",0.88),
 (r"אקטואליה|ביטחון|משמר הגבול|צבא|פוליטיק|חדשות","current-affairs",0.88),
 (r"אמנות|אומנות|ספרות|קולנוע|רקדן|מוזיקה|תרבות","culture-art",0.89),
 (r"יהדות|קבלה|תנך|תנ״ך|פרשת השבוע|מסורת","judaism-spirit",0.89),
 (r"זוגיות|יחסים|תקשורת זוגית","relationships",0.90),
 (r"טיול|מסע|גאוגרפ|ארצות|מסביב לעולם","travel-geography",0.87),
 (r"בינה מלאכותית|דיגיטל|טכנולוגיה|אינטרנט|מחשבים","digital-tech",0.91)]
RULES["seniors"]=[
 (r"נומרולוג|קבלה|הרצאה|מפגש עם מרצה","senior-lectures",0.88),
 (r"סריג|סורגים|יצירה|סדנ|הכנת תליונים|חלוקי נחל|ציור","senior-workshops",0.91),
 (r"סיור|טיול","senior-trips",0.96),
 (r"קריוקי|שירה|מוזיקה|מוסיק|נגינה|קונצרט","senior-music",0.90),
 (r"ריקודי עם|הרקדה|דיסקו|ריקוד","senior-dance",0.92),
 (r"יוגה|פילאטיס|התעמלות|כושר|תנועה","senior-sport",0.89),
 (r"בריאות|רפואה|תזונה|אורח חיים בריא","senior-health",0.91),
 (r"קפה חברתי|מפגש חברתי|מועדון חברתי","senior-social",0.90),
 (r"הצגה|תיאטרון|מחזה|פסטיבל|מופע","senior-culture",0.87),
 (r"דיגיטל|טכנולוגיה|מחשבים|טלפון חכם|אינטרנט","senior-digital",0.94)]
RULES["theatre"]=[
 (r"מחזמר|תיאטרון מוזיקלי","musical",0.96),
 (r"קומדיה|הצגה קומית","comedy",0.94),
 (r"דרמה|מחזה דרמטי","drama",0.91),
 (r"הפקת מקור|הפקה מקורית","original-production",0.94),
 (r"מונודרמה|הצגת יחיד","one-person-show",0.96),
 (r"רפרטוארי","repertory-theatre",0.94)]
RULES["kids"]=[
 (r"שעת סיפור|סיפור עם|מספר(?:ת)? סיפורים|הקראת סיפור","story-time",0.99),
 (r"סדנ(?:ה|ת) (?:יצירה )?(?:ל)?ילדים|יצירה לילדים","kids-workshops",0.94),
 (r"פסטיבל (?:ל)?ילדים|פסטיבל ילד","kids-festival",0.95),
 (r"הצגת ילדים|הצגה לילדים|הצגה מבית|תיאטרון ילדים|הצגה - Live|הדרדסים ההצגה|חיפזון וזהירון","kids-theatre",0.95),
 (r"מופע ילדים|מופע לכל המשפחה|מופע קסמים","kids-shows",0.88),
 (r"הורה וילד|הורה-ילד","parent-child",0.94),
 (r"פעילות לכל המשפחה|פעילות משפחתית","family-activity",0.88)]
RULES["sport"]=[
 (r"כדוריד|handball","handball",0.98),
 (r"כדורעף|volleyball","volleyball",0.98),
 (r"כדורסל|basketball","basketball",0.98),
 (r"כדורגל|football","football",0.98),
 (r"גלישה|סאפ|חתירה","water-sports",0.90),
 (r"מרוץ|מירוץ|ריצת","running-races",0.95),
 (r"טורניר","tournaments",0.95)]
RULES["community"] += [
 (r"טקס|יום העלייה|יום העליה","ceremonies",0.89),
 (r"עדות|יהדות הודו|מורשת קהילה","communities-heritage",0.90),
 (r"הוקרה|מצדיעים","tribute-events",0.90),
 (r"ערב נשים|לנשים בלבד","women-events",0.95)]
RULES["music"] += [
 (r"מוזיקה ישראלית|שירי ארץ ישראל","israeli-music",0.91),
 (r"מוזיקת עולם|מוסיקת עולם|נפוליטנ|איסטנבול|מרסיי","world-music",0.87),
 (r"זמר|זמרת|להקה|להקות|מופע שירים","artists-bands",0.85)]
RULES["cinema"] += [(r"הקרנת סרט|סרט ומפגש|סרט ושיח","other-cinema",0.91)]
RULES["exhibition"] += [(r"פתיחת תערוכה","exhibition-opening",0.96),(r"תערוכת צילום","photography",0.92)]

# Misfiled primary categories need review, not a fabricated subcategory.
PRIMARY_REVIEW=[
 ("theatre",r"הצגה (?:מבית|לילדים)|הצגת ילדים|הנסיכה והכתר|איילת מטיילת|רינת מטיילת","kids"),
 ("standup",r"קומדיה משפחתית|הצגה קומית","theatre"),
 # Organizers and audiences do not determine the event type.
]

def infer(event,valid,definitions):
    cat=event.get("category")
    title=str(event.get("title") or "")
    defs=definitions.get(cat,{}).get("subcategories",{})
    # 1. Structured source categorization is strongest when it matches the canonical taxonomy.
    source_category=str(event.get("source_category") or event.get("source_primary_category") or "")
    source_sub=str(event.get("source_subcategory") or event.get("source_genre") or "")
    if source_category in valid and source_category!=cat:
        return None,0.0,"source_primary_category_conflict",True
    if source_sub:
        matches=[id for id,info in defs.items() if id in valid.get(cat,set())
                 and (source_sub==id or source_sub==info.get("label"))]
        if len(matches)==1:
            return matches[0],1.0,"source_explicit_subcategory",False
        if len(matches)>1:
            return None,0.0,"source_ambiguous_subcategory",True

    # 2. An explicit title genre is authoritative, if exactly one non-conflicting
    # category matches. 3. Then analyze description evidence.
    content=" ".join(str(event.get(k) or "") for k in
                     ("short_pitch","event_summary","description","long_description","series_description"))
    # For senior events, classify the explicit activity format before secondary themes:
    # a guided tour about history remains a tour, and a panel remains a lecture.
    if cat=="seniors":
        format_rules=[
            (r"סיור|טיול|יציאה\s+לסיור","senior-trips"),
            (r"סדנ|עיסת נייר|עיצוב ספגניות|הכנת תליונים","senior-workshops"),
            (r"ספורט|תנועה|יוגה|פילאטיס|כושר|התעמלות","senior-sport"),
            (r"פאנל|הרצאה|שיחה|מפגש העשרה|נומרולוגיה|נמרולוגיה","senior-lectures"),
            (r"קריוקי|שירה בציבור|מעגל מתופפים|קונצרט|שירה","senior-music"),
            (r"הצגה|תיאטרון|פסטיבל|מופע","senior-culture"),
        ]
        for field,evidence_kind in ((title,"title"),(content,"description")):
            for pattern,subcategory in format_rules:
                if subcategory in valid.get(cat,set()) and re.search(pattern,field,re.I):
                    return subcategory,0.97,evidence_kind,False
    for field,evidence_kind in ((title,"title"),(content,"description")):
        matches=[(sub,conf,pattern) for pattern,sub,conf in RULES.get(cat,[])
                 if sub in valid.get(cat,set()) and re.search(pattern,field,re.I)]
        # Use exact taxonomy label and approved evidence cues, not category-name guesses.
        for subid,info in defs.items():
            if subid not in valid.get(cat,set()):
                continue
            for phrase in info.get("positive_evidence",[]):
                if phrase and re.search(r"(?<!\\w)"+re.escape(phrase)+r"(?!\\w)",field,re.I):
                    matches.append((subid,0.97,phrase))
                    break
        if matches:
            candidates={}
            for sub,conf,pattern in matches:
                candidates[sub]=max(conf,candidates.get(sub,0))
            if len(candidates)>1:
                return None,0.0,evidence_kind+"_conflict",True
            sub=next(iter(candidates))
            return sub,candidates[sub],evidence_kind,False
    return None,0.0,"needs_source_research",False

def run():
    events=json.loads(FEED.read_text(encoding="utf-8")).get("events",[])
    taxonomy=json.loads(TAXONOMY.read_text(encoding="utf-8")).get("primary_categories",[])
    valid={g["id"]:{s["id"] for s in g.get("subcategories",[])} for g in taxonomy}
    definitions=json.loads(DEFINITIONS.read_text(encoding="utf-8"))["categories"]
    counts=Counter()
    findings=[]
    for e in events:
        cat=e.get("category"); sub=e.get("subcategory"); title=str(e.get("title") or "")
        if cat not in valid:
            counts["unknown_category"]+=1;continue
        if sub in valid[cat]:
            counts["already_valid"]+=1;continue
        counts["missing_or_invalid"]+=1
        candidate,confidence,evidence,conflict=infer(e,valid,definitions)
        primary_review=next((suggested for current,pattern,suggested in PRIMARY_REVIEW
                             if current==cat and re.search(pattern,title,re.I)),None)
        if primary_review:
            counts["primary_category_review"]+=1
        if e.get("subcategory_manual_override"):
            candidate,confidence,evidence=None,0.0,"manual_lock"
        if candidate:
            counts["staged_candidate"]+=1
            if conflict:counts["conflicting_evidence"]+=1
            elif primary_review:counts["primary_category_review_blocked"]+=1
            elif ((evidence in ("title","source_explicit_subcategory") and confidence>=0.90) or (evidence=="description" and confidence>=0.95)):
                counts["ready_for_guarded_application"]+=1
            elif confidence>=0.85:counts["review_medium_confidence"]+=1
            else:counts["review_low_confidence"]+=1
        else:
            counts["needs_contextual_review"]+=1
            if evidence=="needs_source_research":counts["needs_source_research"]+=1
        status="suggestion_only" if candidate else "needs_review"
        if conflict or confidence<0.85 or primary_review:status="needs_review"
        findings.append({"event_id":e.get("event_id"),"title":title,"category":cat,"existing_subcategory":sub,
                         "suggested_subcategory":candidate,"confidence":confidence,"evidence_field":evidence,
                         "conflict":conflict,"primary_category_review_proposed":primary_review,"status":status})
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({"city":"ashdod","publication_enabled":False,"generated_at":datetime.now(timezone.utc).isoformat(),"total":len(events),
                      "counts":dict(counts),"events":findings},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"total":len(events),"counts":dict(counts)},ensure_ascii=False))

if __name__=="__main__":run()

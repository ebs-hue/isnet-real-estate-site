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
  "kids":[(r"חיפזון וזהירון|הצגת ילדים|שעת סיפור","kids-theatre"),(r"סדנ(?:ה|ת) ילדים","kids-workshops")],
  "music":[(r"MALEVO","dance-performance"),(r"מופע מחווה","tribute-shows"),(r"שירה בציבור","sing-along"),(r"קונצרט","concerts")],
  "theatre":[(r"קומדיה","comedy"),(r"מחזמר","musical")],
  "community":[(r"ריקודי עם","folk-dancing"),(r"גדולות מהחיים","women-events")],
  "sport":[(r"מ\\.ס\\.? אשדוד","ms-ashdod-home-games")],
  "cinema":[(r"סינמה סיטי","cinema-city"),(r"הוט סינמה","hot-cinema")],
}
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
        candidate=None
        if not e.get("subcategory_manual_override"):
            for pattern,subid in RULES.get(cat,[]):
                if re.search(pattern,title,re.I) and subid in valid[cat]:
                    candidate=subid;break
        if candidate:counts["staged_candidate"]+=1
        else:counts["needs_contextual_review"]+=1
        findings.append({"event_id":e.get("event_id"),"title":title,"category":cat,"existing_subcategory":sub,
                         "suggested_subcategory":candidate,"status":"suggestion_only" if candidate else "needs_review"})
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({"city":"ashdod","publication_enabled":False,"total":len(events),
                      "counts":dict(counts),"events":findings},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"total":len(events),"counts":dict(counts)},ensure_ascii=False))

if __name__=="__main__":run()

#!/usr/bin/env python3
"""Read-only editorial audit. Preserve concerns; never publish or delete content."""
import json, re
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview/ashdod/data/events.json"
QUALITY=ROOT/"events-preview/admin/data/content-quality-ashdod.json"
OUTPUT=ROOT/"events-preview/admin/data/editorial-audit-ashdod.json"
PATTERNS={
 "internal_research_note":[r"העמוד אינו מפרט",r"המקור אינו מפרט",r"יש לבדוק",r"יש לאמת",r"לא ניתן לאמת",r"לא נמצאו פרטים",r"נדרש בירור",r"לפני פרסום",r"לא ברור מן המקור",r"יש לעיין בעמוד",r"לפי (?:עמוד|אתר|פרסום|המקור|המידע באתר)",r"על פי (?:עמוד|אתר|פרסום|המקור)",r"לפי (?:FRIENDS|סמארטיקט|טיקצ.אק|המשכן)"],
 "editorial_placeholder":[r"מידע נוסף בקרוב",r"פרטים יעודכנו",r"תיאור האירוע יעודכן"],
}
def text(e):
 return " ".join(str(e.get(k) or "") for k in ("long_description","short_pitch","event_summary","description","series_description"))
def main():
 doc=json.loads(DATA.read_text(encoding="utf-8"))
 quality=json.loads(QUALITY.read_text(encoding="utf-8"))
 scores={str(e.get("event_id")):e for e in quality.get("events",[])}
 rows=[]
 for e in doc.get("events",[]):
  eid=str(e.get("event_id") or "")
  t=text(e)
  flags=[]
  for typ,patterns in PATTERNS.items():
   for pat in patterns:
    if re.search(pat,t):
     flags.append({"type":typ,"match":pat})
  if len(t.strip())<110: flags.append({"type":"thin_public_description"})
  prior=scores.get(eid,{})
  if prior.get("severity") in ("critical","needs_review"):
   flags.append({"type":"prior_quality_flag","severity":prior.get("severity"),"score":prior.get("score")})
  if flags:
   rows.append({"event_id":eid,"title":e.get("title"),"start_date":e.get("start_date"),"flags":flags,"preserved_excerpt":t[:1800],"source_url":e.get("detail_source_url") or e.get("ticket_url"),"resolution_status":"requires_editorial_review"})
 OUTPUT.parent.mkdir(parents=True,exist_ok=True)
 OUTPUT.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"mode":"read_only","total_events":len(doc.get("events",[])),"flagged_events":len(rows),"events":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"total":len(doc.get("events",[])),"flagged":len(rows)},ensure_ascii=False))
if __name__=="__main__":main()

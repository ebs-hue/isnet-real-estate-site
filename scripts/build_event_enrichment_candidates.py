#!/usr/bin/env python3
"""Build conservative production-level enrichment suggestions; never modify public events.
Priority: original event -> same show across national boards (any city) -> subcategory image bank -> category image bank.
"""
import json,re
from pathlib import Path
from difflib import SequenceMatcher
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview/admin/data"
def read(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
def normal(value):
    s=re.sub(r"[^\u0590-\u05ffA-Za-z0-9 ]"," ",str(value or "").lower())
    s=re.sub(r"\\b(?:2026|2027)\\b"," ",s)
    return " ".join(s.split())
def candidate_records():
    out=[]
    for item in read(DATA/"national-events-discovery.json").get("candidates",[]):
        out.append({"title":item.get("title_candidate"),"url":item.get("source_url"),"source_id":item.get("source_id"),"image_candidate":item.get("image_candidate_url"),"reuse_authorized":False})
    for item in read(DATA/"friends-discovery.json").get("candidates",[]):
        out.append({"title":item.get("title"),"url":item.get("production_url"),"source_id":"friends-hist","image_candidate":None,"reuse_authorized":False})
    return out
def main():
    feed=read(ROOT/"events-preview/ashdod/data/events.json").get("events",[])
    bank=read(DATA/"subcategory-image-map.json").get("categories",{})
    config=read(DATA/"event-source-priority.json")
    allowed=set(config.get("enrichment_pipeline",{}).get("stage_board_categories",[]))
    candidates=candidate_records()
    report=[]
    for event in feed:
        category=event.get("category");sub=event.get("subcategory")
        original_image=bool(event.get("image_url") and event.get("image_publishable") is True and event.get("image_verified") is True)
        original_description=bool(event.get("long_description") or event.get("description"))
        name=normal(event.get("title"))
        matches=[]
        if category in allowed and len(name)>=7:
            for item in candidates:
                other=normal(item["title"])
                # National list cards may prepend dates/locations/prices; exact production title
                # must be present as a substantial contiguous phrase, or near-identical.
                if len(other)<7:continue
                score=SequenceMatcher(None,name,other).ratio()
                exact=(name==other)
                if exact or (score>=0.94 and len(name)>=10 and len(other)>=10):
                    matches.append({"source_id":item["source_id"],"source_url":item["url"],"title":item["title"],"match_score":round(score,3),"image_candidate_url":item["image_candidate"],"image_reuse_authorized":False})
        section=bank.get(category,{})
        sub_images=section.get("subcategories",{}).get(sub,{}).get("image_files",[]) if sub else []
        cat_images=section.get("category_images",[])
        image_step="original_source" if original_image else ("same_production_source_requires_image_rights_review" if any(m["image_candidate_url"] for m in matches) else ("subcategory_bank" if sub_images else ("primary_category_bank" if cat_images else "needs_image")) )
        report.append({"event_id":event.get("event_id"),"title":event.get("title"),"category":category,"subcategory":sub,"original_description_present":original_description,"original_image_verified":original_image,"same_production_candidates":matches[:5],"image_next_step":image_step,"subcategory_image_files":sub_images,"category_image_files":cat_images,"editorial_publication_approved":False})
    path=DATA/"event-enrichment-candidates-ashdod.json"
    path.write_text(json.dumps({"events_checked":len(report),"publication_enabled":False,"matches_need_production_verification":True,"image_rights_review_required":True,"events":report},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Audited",len(report),"events. Candidate matches",sum(bool(x["same_production_candidates"]) for x in report))
if __name__=="__main__":main()

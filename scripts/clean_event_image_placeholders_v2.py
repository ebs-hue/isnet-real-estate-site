#!/usr/bin/env python3
import json, time
from collections import Counter
from pathlib import Path

root=Path(__file__).resolve().parents[1]
events_path=root/"events-preview"/"ashdod"/"data"/"events.json"
report_path=root/"events-preview"/"ashdod"/"data"/"image-enrichment-report.json"
data=json.loads(events_path.read_text(encoding="utf-8"))
bad=("/languages/il.gif","artistshadow","eventnew.jpg","no_pic","no-pic","placeholder","smarticket_logo","microsoft_oauth_logo","google_oauth_logo","facebook_oauth","oauth_logo","oauth","_logo_")
cleared=0
for e in data.get("events",[]):
    u=(e.get("image_url") or "").lower()
    if u and any(x in u for x in bad):
        e["image_url"]=None
        e["image_source"]=None
        e["image_credit"]=None
        e["image_publishable"]=False
        e["image_verified"]=False
        e["image_rights_status"]="rejected_generic_asset"
        e["image_strategy"]="rejected_generic_asset"
        e["image_origin_url"]=None
        e["thumbnail_ready"]=False
        e["thumbnail_url"]=None
        cleared+=1

events=data.get("events",[])
missing=[e for e in events if not(e.get("image_url") and e.get("image_publishable") is True)]
source_counts=Counter()
category_counts=Counter()
for e in missing:
    category_counts[e.get("category") or "unknown"]+=1
    for s in e.get("sources",[]): source_counts[s.get("name") or "unknown"]+=1

report={
    "generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
    "total_events":len(events),
    "events_with_publishable_images":len(events)-len(missing),
    "events_still_missing_images":len(missing),
    "stats":{"generic_images_cleared":cleared},
    "missing_by_source":dict(source_counts),
    "missing_by_category":dict(category_counts),
    "missing":[{"event_id":e.get("event_id"),"title":e.get("title"),"reason":"no_verified_source_image"} for e in missing]
}
events_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"cleared={cleared} missing={len(missing)}")

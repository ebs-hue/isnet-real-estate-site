#!/usr/bin/env python3
"""Diagnose all unmatched Ashdod stage occurrences after national board pull."""
import json,re,html
from collections import Counter
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"events-preview/admin/data"
def norm(s):
    return " ".join(re.sub(r"[^\w\u0590-\u05ff ]"," ",html.unescape(str(s or "")).lower()).split())
def main():
    today=datetime.now(ZoneInfo("Asia/Jerusalem")).date().isoformat()
    existing=json.loads((ROOT/"events-preview/ashdod/data/events.json").read_text(encoding="utf-8"))["events"]
    source=json.loads((BASE/"unified-stage-events-ashdod-rishon.json").read_text(encoding="utf-8"))["events"]
    source=[x for x in source if x.get("city")=="ashdod" and str(x.get("date_time") or "")[:10]>=today]
    old=[x for x in existing if x.get("category") in ("music","standup","kids","theatre") and str(x.get("start_date") or "")>=today]
    indexes={}
    for row in source:indexes.setdefault(norm(row.get("title")),[]).append(row)
    results=[];causes=Counter()
    for item in old:
        matches=indexes.get(norm(item.get("title")),[])
        same_date=[x for x in matches if str(x.get("date_time") or "")[:10]==item.get("start_date")]
        viable=[x for x in same_date if x.get("image_url")]
        reason=("not_in_collected_sources" if not matches else
                "different_date" if not same_date else
                "source_missing_image" if not viable else "venue_mismatch_or_already_processed")
        causes[reason]+=1
        results.append({"event_id":item.get("event_id"),"title":item.get("title"),"date":item.get("start_date"),
          "venue":item.get("venue"),"reason":reason,
          "sources_with_title":len(matches),"sources_with_date":len(same_date),
          "sources_with_image":len(viable)})
    out={"generated_at":datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(),
      "future_stage_count":len(old),"ashdod_source_occurrences":len(source),
      "causes":dict(causes),"events":results,"cms_modified":False}
    (BASE/"stage-coverage-diagnostics.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"future_stage_count":len(old),"causes":dict(causes)},ensure_ascii=False))
if __name__=="__main__":main()

#!/usr/bin/env python3
"""Quality gate for replacing stage events with national board listings."""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"events-preview/admin/data/unified-stage-events-ashdod-rishon.json"
OUT=ROOT/"events-preview/admin/data/stage-rebuild-readiness.json"
def main():
    data=json.loads(SOURCE.read_text(encoding="utf-8"))
    today=datetime.now(ZoneInfo("Asia/Jerusalem")).date().isoformat()
    report={"checked_at":datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(),"cities":{},"feeds_unchanged":True}
    for city in ("ashdod","rishon-lezion"):
        feed=json.loads((ROOT/f"events-preview/{city}/data/events.json").read_text(encoding="utf-8"))
        old=[x for x in feed.get("events",[]) if x.get("category") in {"music","standup","kids","theatre"} and str(x.get("start_date") or "")>=today]
        new=[x for x in data["events"] if x.get("city")==city and str(x.get("date_time") or "")[:10]>=today]
        report["cities"][city]={"existing_future_stage":len(old),"national_candidates":len(new),
          "with_image":sum(bool(x.get("image_url")) for x in new),
          "with_description":sum(bool(x.get("description")) for x in new),
          "ready_for_full_replace":len(new)>=len(old)*0.8 and len(new)>=20}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()

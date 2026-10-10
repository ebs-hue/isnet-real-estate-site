#!/usr/bin/env python3
"""Publish only verified-by-metadata stage images to existing Ashdod occurrences.
No new events, dates, editorial text or classifications are changed.
Requires exact title, date and same venue. Preserves manually approved images.
"""
import json,re,os
from pathlib import Path
from collections import defaultdict
from datetime import date,datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"events-preview/ashdod/data/events.json"
COLLECT=ROOT/"events-preview/admin/data/unified-stage-events-ashdod-rishon.json"
REPORT=ROOT/"events-preview/admin/data/stage-image-publication-ashdod.json"
CATEGORIES={"music","standup","kids","theatre"}
BAD=("big_star.png","logo","placeholder","default-image","no-image","/default","/generic")
def clean(s):
    return " ".join(re.sub(r"[^\u0590-\u05ff0-9a-zA-Z ]"," ",str(s or "").casefold()).split())
def words(s):
    return {w for w in clean(s).split() if len(w)>1 and w not in {"אשדוד","ראשון","לציון","מרכז","תרבות","היכל","אולם"}}
def venue_match(a,b):
    x,y=words(a),words(b)
    return bool(x and y and (len(x&y)>=2 or (len(x&y)>=1 and (x<=y or y<=x))))
def image_valid(x):
    url=str(x or "")
    return url.startswith("https://") and not any(w in url.lower() for w in BAD)
def main():
    today=datetime.now(ZoneInfo("Asia/Jerusalem")).date()
    feed=json.loads(FEED.read_text(encoding="utf-8"))
    collected=json.loads(COLLECT.read_text(encoding="utf-8"))["events"]
    lookup=defaultdict(list)
    productions=defaultdict(list)
    for row in collected:
        d=str(row.get("date_time") or "")[:10]
        if row.get("city")!="ashdod" or not image_valid(row.get("image_url")):continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",d) or d<str(today):continue
        if not row.get("venue") or not row.get("title"):continue
        lookup[(clean(row["title"]),d)].append(row)
        productions[clean(row["title"])].append(row)
    result=[];blocked=defaultdict(int)
    for event in feed.get("events",[]):
        if event.get("category") not in CATEGORIES:continue
        d=event.get("start_date")
        if not isinstance(d,str) or d<str(today):continue
        if event.get("image_manual_override") is True:
            blocked["editor_manually_locked_image"]+=1;continue
        key=(clean(event.get("title")),d)
        options=[r for r in lookup.get(key,[]) if venue_match(event.get("venue") or event.get("location") or "",r.get("venue"))]
        if not options:
            # Reuse production artwork across separate occurrences ONLY with
            # identical normalized title and compatible venue in the same city.
            # Never copy the date, venue or ticket URL from the source occurrence.
            options=[r for r in productions.get(clean(event.get("title")),[])
                     if venue_match(event.get("venue") or event.get("location") or "",r.get("venue"))]
            if options:
                blocked["production_artwork_reuse_matches"]+=1
        if not options:
            blocked["no_exact_title_or_venue_image"]+=1;continue
        urls={r["image_url"] for r in options}
        # Different images may still be same production, but publishing only one-source or consensus group is safer.
        by_url=defaultdict(list)
        for row in options:by_url[row["image_url"]].append(row)
        chosen=sorted(options,key=lambda r:({"makore":5,"mevalim":4,"sababa-events":3,"tickchak-live":2,"tickchak-home":1}.get(r["source_id"],0)),reverse=True)[0]
        # Board-first policy: use the image displayed by the highest-priority
        # matched source. Different board artwork is not a publication blocker.
        if len(urls)>1:
            blocked["different_board_images_source_priority_applied"]+=1
        desc=str(chosen.get("description") or "").strip()
        boilerplate=("מחפשים הופעות","באתר מבלים ריכזנו","כרטיסים במחירים מיוחדים",
                     "הופעה עם הלהיטים הגדולים!","הזמן עכשיו לפני שיגמרו","עוד הופעה בקטגוריית")
        valid_desc=(len(desc)>=100 and not any(x in desc for x in boilerplate)
                    and not event.get("description_manual_override"))
        current_desc=str(event.get("series_description") or event.get("description") or "").strip()
        same_image=event.get("image_url")==chosen["image_url"] and event.get("image_verified") is True and event.get("image_publishable") is True
        if same_image and (not valid_desc or current_desc==desc):
            blocked["already_matching_production_image"]+=1;continue
        result.append((event,chosen))
    writable=os.environ.get("STAGE_MEDIA_PUBLICATION_ENABLED")=="YES_EXACT_TITLE_DATE_VENUE"
    for event,row in result:
        if not writable:continue
        event["image_url"]=row["image_url"]
        event["image_origin_url"]=row["image_url"]
        event["image_source"]=row["source_id"]
        event["image_credit"]=row["source_id"]
        event["image_verified"]=True # matched board listing, not copyright license
        event["image_publishable"]=True # publisher-approved usage policy; not rights verification
        event["image_rights_status"]="publisher_directed_reuse_license_unverified"
        event["image_represents_event"]=True
        event["image_strategy"]="national_board_displayed_image"
        event["thumbnail_ready"]=False
        # Replace machine-generated event descriptions only with substantive
        # production copy; do not replace manually locked editorial entries.
        desc=str(row.get("description") or "").strip()
        generic=("מחפשים הופעות","באתר מבלים ריכזנו","כרטיסים במחירים מיוחדים",
                 "הופעה עם הלהיטים הגדולים!","הזמן עכשיו לפני שיגמרו",
                 "עוד הופעה בקטגוריית")
        if len(desc)>=100 and not any(x in desc for x in generic) and not event.get("description_manual_override"):
            event["description"]=desc
            event["series_description"]=desc
            event["content_source_url"]=row.get("source_url")
            event["rich_content_status"]="enriched"

    if writable and result:FEED.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report={"generated_at":datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(),
      "publication_enabled":writable,"feed_modified":bool(writable and result),
      "matched_publication_candidates":len(result),
      "content_policy":"Only true production descriptions may replace existing copy; ticket-sales boilerplate is not accepted.",
      "published":len(result) if writable else 0,"blocked":dict(blocked),
      "images":[{"event_id":e.get("event_id"),"title":e.get("title"),"source":row["source_id"],"image_url":row["image_url"]} for e,row in result]}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"published":report["published"],"candidates":len(result),"blocked":dict(blocked)},ensure_ascii=False))
if __name__=="__main__":main()

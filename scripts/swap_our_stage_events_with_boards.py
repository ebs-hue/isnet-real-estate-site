#!/usr/bin/env python3
"""Replace our auto-created stage event occurrences with matched board records.
Only title+date matches; preserve all unrelated events and manual editor locks.
"""
import hashlib,html,json,os,re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
COLLECT=ROOT/"events-preview/admin/data/unified-stage-events-ashdod-rishon.json"
REPORT=ROOT/"events-preview/admin/data/stage-board-swap-report.json"
CATS={"music","standup","kids","theatre"}
RANK={"mevalim":5,"makore":4,"sababa-events":3,"tickchak-live":2,"tickchak-home":1}
def normal(x):
    return " ".join(re.sub(r"[^\w\u0590-\u05ff]+"," ",html.unescape(str(x or "")).lower()).split())
def good_image(x):
    x=str(x or "")
    return x.startswith("https://") and not any(y in x.lower() for y in ("big_star.png","placeholder","default-image","logo"))
def good_copy(s):
    s=html.unescape(str(s or "")).strip()
    return s if len(s)>=100 and not any(w in s for w in ("מחפשים הופעות","באתר מבלים ריכזנו","כרטיסים במחירים מיוחדים","הופעה עם הלהיטים הגדולים","עוד הופעה בקטגוריית")) else ""
def main():
    now=datetime.now(ZoneInfo("Asia/Jerusalem"))
    today=now.date().isoformat()
    ingestion_time=now.isoformat()
    collected=json.loads(COLLECT.read_text(encoding="utf-8"))
    index=defaultdict(list)
    for x in collected["events"]:
        d=str(x.get("date_time") or "")[:10]
        if x.get("city") in ("ashdod","rishon-lezion") and d>=today and re.fullmatch(r"\d{4}-\d{2}-\d{2}",d):
            index[(x["city"],normal(x.get("title")),d)].append(x)
    report={"at":datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(),"cities":{},"published":False}
    enabled=os.getenv("STAGE_SWAP_FROM_BOARDS")=="YES_MATCHED_EVENTS_ONLY"
    for city in ("ashdod","rishon-lezion"):
        path=ROOT/f"events-preview/{city}/data/events.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        kept=[];replacement=[];removed=[];ignored=0
        for e in data["events"]:
            if e.get("category") not in CATS or not (str(e.get("event_id") or "").startswith(("auto_","evt_"))):
                kept.append(e);continue
            if e.get("human_manual_override") is True or e.get("description_manual_override") is True or e.get("image_manual_override") is True:
                kept.append(e);continue
            options=index.get((city,normal(e.get("title")),str(e.get("start_date") or "")),[])
            if not options:
                kept.append(e);ignored+=1;continue
            selected=sorted(options,key=lambda x:(bool(good_image(x.get("image_url"))),bool(good_copy(x.get("description"))),RANK.get(x.get("source_id"),0)),reverse=True)[0]
            if not selected.get("date_time") or not selected.get("venue"):
                kept.append(e);continue
            copy=good_copy(selected.get("description"))
            img=selected.get("image_url") if good_image(selected.get("image_url")) else None
            new={"event_id":e["event_id"],"title":html.unescape(selected["title"]),"city":e.get("city"),"category":e["category"],
                 "subcategory":e.get("subcategory"),"start_date":selected["date_time"][:10],
                 "start_time":selected["date_time"][11:16],"venue":html.unescape(selected["venue"]),
                 "status":"active","description":copy,"series_description":copy,
                 "ticket_url":selected.get("tickets_url") or e.get("ticket_url"),
                 "purchase_url":selected.get("tickets_url") or e.get("purchase_url"),
                 "image_url":img,"image_origin_url":img,"image_source":selected.get("source_id"),
                 "image_verified":bool(img),"image_publishable":bool(img),
                 "image_represents_event":bool(img),"image_strategy":"national_board_displayed_image",
                 "image_rights_status":"publisher_directed_reuse_license_unverified" if img else "unknown",
                 "content_source_url":selected.get("source_url"),"rich_content_status":"enriched" if copy else "source_copy_unavailable",
                 "source":"national_stage_boards","source_event_id":e["event_id"],"imported_at":e.get("imported_at") or ingestion_time,"last_imported_at":ingestion_time}
            replacement.append(new);removed.append(e["event_id"])
        if enabled and replacement:
            data["events"]=kept+replacement
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        report["cities"][city]={"replaced":len(replacement) if enabled else 0,"ready":len(replacement),
            "unmatched_originals_retained":ignored,"original_event_ids_preserved":True}
    # Import additional future occurrences, even when the source category is
    # not present in our taxonomy. Preserve its exact label as source_category.
    for city in ("ashdod","rishon-lezion"):
        path=ROOT/f"events-preview/{city}/data/events.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        seen={(normal(e.get("title")),str(e.get("start_date") or ""),str(e.get("start_time") or "")[:5])
              for e in data.get("events",[])}
        new=[];skipped=0
        for (source_city,title,date),items in index.items():
            if source_city!=city:continue
            for group in [items]:
                selected=sorted(group,key=lambda x:(bool(good_image(x.get("image_url"))),bool(good_copy(x.get("description"))),RANK.get(x.get("source_id"),0)),reverse=True)[0]
                tm=str(selected.get("date_time") or "")[11:16]
                key=(title,date,tm)
                if key in seen:continue
                if not selected.get("title") or not selected.get("venue") or not re.fullmatch(r"\d{2}:\d{2}",tm):
                    skipped+=1;continue
                raw=str(selected.get("category") or selected.get("source_category") or "מופעי במה").strip()
                words=normal(selected["title"]+" "+raw)
                cat=("standup" if "סטנד" in words else "kids" if any(w in words for w in ("ילדים","משפחה")) else
                     "theatre" if any(w in words for w in ("הצגה","מחזמר","תיאטרון","קומדיה")) else "music")
                image=selected.get("image_url") if good_image(selected.get("image_url")) else None
                desc=good_copy(selected.get("description"))
                uid=hashlib.sha256(("|".join([city,title,date,tm])).encode()).hexdigest()[:18]
                new.append({"event_id":"board_"+uid,"title":html.unescape(selected["title"]),
                    "city":"אשדוד" if city=="ashdod" else "ראשון לציון","category":cat,
                    "source_category":raw,"start_date":date,"start_time":tm,
                    "venue":html.unescape(selected["venue"]),"status":"active","description":desc,
                    "series_description":desc,"image_url":image,"image_origin_url":image,
                    "image_source":selected["source_id"],"image_verified":bool(image),
                    "image_publishable":bool(image),"image_rights_status":"publisher_directed_reuse_license_unverified",
                    "image_strategy":"national_board_displayed_image",
                    "ticket_url":selected.get("tickets_url"),"purchase_url":selected.get("tickets_url"),
                    "content_source_url":selected.get("source_url"),"source":"national_stage_boards","imported_at":ingestion_time,"last_imported_at":ingestion_time})
                seen.add(key)
        if enabled and new:
            data["events"].extend(new)
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        report["cities"][city]["new_imported"]=len(new) if enabled else 0
        report["cities"][city]["invalid_source_rows_skipped"]=skipped
    # Remove duplicate records created by our earlier agents when a matching
    # nationally sourced occurrence is already in the same city feed.
    # Source identity and occurrence date/time, not category or approval flags,
    # decide which record is preferred. Manually protected records remain.
    for city in ("ashdod","rishon-lezion"):
        path=ROOT/f"events-preview/{city}/data/events.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        groups=defaultdict(list)
        for e in data["events"]:
            dt=(str(e.get("start_date") or ""),str(e.get("start_time") or "")[:5])
            if e.get("category") in CATS and dt[0]>=today and dt[1] and normal(e.get("title")):
                groups[(normal(e.get("title")),*dt)].append(e)
        drop=set()
        for key,group in groups.items():
            board=[e for e in group if e.get("source")=="national_stage_boards" or str(e.get("event_id") or "").startswith("board_")]
            if not board:continue
            # Retain one national-board card for each occurrence; manual locks
            # are excluded from deletion.
            preferred=next((e for e in board if str(e.get("event_id") or "").startswith("board_")),board[0])
            for e in group:
                if e is preferred:continue
                if e.get("human_manual_override") is True or e.get("image_manual_override") is True or e.get("description_manual_override") is True:continue
                if e.get("source")=="national_stage_boards" or str(e.get("event_id") or "").startswith(("auto_","evt_","board_")):
                    drop.add(id(e))
        removed_duplicates=sum(id(e) in drop for e in data["events"])
        if enabled and drop:
            data["events"]=[e for e in data["events"] if id(e) not in drop]
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
        report["cities"][city]["duplicate_agent_records_removed"]=removed_duplicates if enabled else 0
        report["cities"][city]["duplicates_preserved_if_editor_locked"]=True
    report["published"]=enabled and any(x["replaced"] or x.get("new_imported") or x.get("duplicate_agent_records_removed") for x in report["cities"].values())
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()

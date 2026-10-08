#!/usr/bin/env python3
from __future__ import annotations
import json, time
from collections import Counter, defaultdict
from pathlib import Path
import fast_fill_event_images_from_listings as base

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview"/"ashdod"/"data"/"events.json"
REPORT=ROOT/"events-preview"/"ashdod"/"data"/"image-pilot-25-report.json"
LIMIT=25

def main():
    started=time.monotonic()
    doc=json.loads(DATA.read_text(encoding="utf-8"))
    all_events=doc.get("events") or []

    # HARD SAFETY GATE: only truly empty image slots can enter the pilot.
    targets=[e for e in all_events if base.in_horizon(e) and not e.get("image_url") and not e.get("thumbnail_url")][:LIMIT]
    target_ids={e.get("event_id") for e in targets}
    before={e["event_id"]:json.dumps(e,ensure_ascii=False,sort_keys=True) for e in all_events if e.get("event_id") not in target_ids}

    stats=Counter()
    filled=[]
    bank=base.load_bank_reuse()

    # 1. Exact approved production reuse.
    for e in targets:
        key=base.norm(e.get("production_name") or e.get("series_name") or e.get("title"))
        m=bank.get(key)
        if not m: continue
        full=base.bank_asset_url(m)
        if not full: continue
        thumb="/events-preview/"+m["card_url"].lstrip("/") if m.get("card_url") else full
        e.update({
            "image_url":full,"thumbnail_url":thumb,"thumbnail_ready":bool(thumb),
            "image_origin_url":m.get("origin_url") or full,
            "image_source":m.get("source_url"),"image_credit":m.get("credit"),
            "image_publishable":True,"image_verified":True,
            "image_rights_status":m.get("rights_status") or "verified_reuse",
            "image_strategy":"pilot_exact_media_bank_reuse","media_bank_id":m.get("media_id")
        })
        stats["bank_exact"]+=1
        filled.append({"event_id":e.get("event_id"),"title":e.get("title"),"method":"bank_exact","image":full})

    # 2. Reuse an already-good image only for the exact same normalized title.
    same_title={}
    for e in all_events:
        if e.get("event_id") in target_ids: continue
        if e.get("image_url") and e.get("image_verified") is True and e.get("image_publishable") is True:
            same_title.setdefault(base.norm(e.get("title")),e)
    for e in targets:
        if e.get("image_url") or e.get("thumbnail_url"): continue
        src=same_title.get(base.norm(e.get("title")))
        if not src: continue
        for k in ("image_url","thumbnail_url","thumbnail_ready","image_origin_url","image_source","image_credit","media_bank_id"):
            if k in src: e[k]=src.get(k)
        e.update({
            "image_publishable":True,"image_verified":True,
            "image_rights_status":src.get("image_rights_status") or "verified_reuse",
            "image_strategy":"pilot_same_title_reuse"
        })
        stats["same_title"]+=1
        filled.append({"event_id":e.get("event_id"),"title":e.get("title"),"method":"same_title","image":e.get("image_url")})

    # 3. Search only the target events' official listing sources.
    roots=[]
    for e in targets:
        if e.get("image_url") or e.get("thumbnail_url"): continue
        for s in e.get("sources") or []:
            u=s.get("url") or ""
            if not u: continue
            roots.append(u)
            if "smarticket.co.il" in base.host(u): roots.append(u.rstrip("/")+"/iframe")
    roots=list(dict.fromkeys(roots))
    pages={}
    for root in roots:
        try: pages[root]=base.get_html(root)
        except Exception: pages[root]=None

    options={}
    for e in targets:
        if e.get("image_url") or e.get("thumbnail_url"): continue
        if e.get("detail_source_url"): continue
        rows=[]
        allowed=set()
        for s in e.get("sources") or []:
            u=s.get("url") or ""
            if not u: continue
            allowed.add(u)
            if "smarticket.co.il" in base.host(u): allowed.add(u.rstrip("/")+"/iframe")
        for root in allowed:
            loaded=pages.get(root)
            if not loaded: continue
            markup,final=loaded
            for score,u in base.score_candidates(e,markup,final)[:10]:
                if score>=65: rows.append((score,u,final))
        if rows:
            best={}
            for row in rows:
                if row[1] not in best or row[0]>best[row[1]][0]: best[row[1]]=row
            options[e["event_id"]]=sorted(best.values(),reverse=True)

    # Reject candidate image reused around multiple different pilot titles.
    usage=defaultdict(set)
    byid={e["event_id"]:e for e in targets}
    for eid,rows in options.items():
        for _,u,_ in rows[:5]: usage[u].add(base.norm(byid[eid].get("title")))
    unsafe={u for u,titles in usage.items() if len(titles)>1}

    for e in targets:
        if e.get("image_url") or e.get("thumbnail_url"): continue
        chosen=next((r for r in options.get(e["event_id"],[]) if r[1] not in unsafe),None)
        if not chosen: continue
        score,u,ref=chosen
        try: local=base.download_image(u,ref)
        except Exception:
            stats["download_failed"]+=1
            continue
        e.update({
            "image_url":local,"image_origin_url":u,"image_source":ref,
            "image_credit":"צילום או כרזה: אתר המארגן הרשמי",
            "image_publishable":True,"image_verified":True,
            "image_rights_status":"verified_official_source",
            "image_strategy":"pilot_official_source","thumbnail_ready":False,"thumbnail_url":None
        })
        stats["official_source"]+=1
        filled.append({"event_id":e.get("event_id"),"title":e.get("title"),"method":"official_source","image":u})

    # 4. Last resort only: owned category fallback. Still only on originally-empty slots.
    for e in targets:
        if e.get("image_url") or e.get("thumbnail_url"): continue
        cat=base.representative_category(e)
        asset=base.SYSTEM_FALLBACKS.get(cat,base.SYSTEM_FALLBACKS["community"])
        e.update({
            "image_url":asset,"image_origin_url":asset,
            "image_source":"ISNET internal representative artwork",
            "image_credit":"איור מייצג: ISNET",
            "image_publishable":True,"image_verified":True,
            "image_rights_status":"owned_system_asset",
            "image_strategy":"pilot_representative_fallback",
            "image_represents_event":False,"image_represents_category":True,
            "thumbnail_ready":False,"thumbnail_url":None
        })
        stats["fallback"]+=1
        filled.append({"event_id":e.get("event_id"),"title":e.get("title"),"method":"fallback","image":asset})

    # Verify absolutely nothing outside the 25 candidates changed.
    changed_outside=[]
    for e in all_events:
        eid=e.get("event_id")
        if eid in target_ids: continue
        if before.get(eid)!=json.dumps(e,ensure_ascii=False,sort_keys=True):
            changed_outside.append(eid)
    if changed_outside:
        raise RuntimeError("SAFETY FAILURE: changed non-target events: "+",".join(changed_outside[:10]))

    elapsed=round(time.monotonic()-started,2)
    report={
        "pilot":"ashdod_missing_images_25",
        "selected":len(targets),
        "filled":sum(stats[k] for k in ("bank_exact","same_title","official_source","fallback")),
        "elapsed_seconds":elapsed,
        "stats":dict(stats),
        "non_target_events_changed":0,
        "events":filled,
    }
    DATA.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

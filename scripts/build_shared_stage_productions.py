#!/usr/bin/env python3
"""Build a shared, read-only production candidate registry across ISNET cities.

Only identical normalized titles become *provisional* groups; no show identity,
rights, content, category or cross-city occurrence is approved by this script.
"""
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"events-preview/admin/data"
OUTPUT=DATA/"stage-productions-candidates.json"
ALLOWED={"music","standup","kids","theatre"}
GENERIC={"אירועים באשדוד","אירועים בראשון לציון","כל האירועים","לוח הופעות","לרכישת כרטיסים","פרטים נוספים","sababa.events","אירועים","הופעות"}

def load(name):
    path=DATA/name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def normalize(title):
    text=re.sub(r"[^\w\u0590-\u05ff ]"," ",str(title or "").casefold())
    return " ".join(text.split())

def valid_title(title):
    t=normalize(title)
    return (6<=len(t)<=120 and t not in {normalize(x) for x in GENERIC}
            and len(t.split())<=15 and not re.search(r"\\b(?:יום ראשון|יום שני|יום שלישי|יום רביעי|יום חמישי|יום שישי|יום שבת)\\b",t))

def main():
    sources=load("event-source-priority.json")["sources"]
    known={s["id"] for s in sources if s.get("enabled")}
    candidates=[]
    for x in load("friends-discovery.json").get("candidates",[]):
        if x.get("source_id") not in known or not valid_title(x.get("title")):
            continue
        candidates.append({"title":x["title"],"source_id":x["source_id"],
                           "source_url":x.get("production_url"),"city_hint":x.get("city"),
                           "image_candidate_url":None,"source_detail":"production_page"})
    for x in load("national-events-discovery.json").get("candidates",[]):
        if x.get("source_id") not in known or not valid_title(x.get("title_candidate")):
            continue
        url=x.get("source_url") or ""
        if not urlparse(url).hostname:
            continue
        candidates.append({"title":x["title_candidate"],"source_id":x["source_id"],
                           "source_url":url,"city_hint":x.get("city_hint"),
                           "image_candidate_url":x.get("image_candidate_url"),
                           "source_detail":"national_listing"})
    groups=defaultdict(list)
    for x in candidates:
        groups[normalize(x["title"])].append(x)
    productions=[]
    for key,items in sorted(groups.items()):
        unique={(x["source_id"],x["source_url"]):x for x in items}
        rows=list(unique.values())
        pid="production_candidate_"+hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        productions.append({
            "production_candidate_id":pid,
            "title_candidate":rows[0]["title"],
            "identity_review_status":"provisional_title_match_only",
            "classification_status":"unverified",
            "category":None,"subcategory":None,
            "production_description":None,
            "image_url":None,"image_publishable":False,
            "image_reuse_rights":"not_verified",
            "source_links":rows,
            "cities_seen":sorted({x["city_hint"] for x in rows if x["city_hint"]}),
            "local_occurrences":[],
            "warning":"Do not interpret city hints as confirmed show dates; verify production identity, venue and schedule before linking or publishing."
        })
    output={"generated_at":datetime.now(timezone.utc).isoformat(),
            "type":"shared_stage_production_candidates",
            "stage_categories":sorted(ALLOWED),
            "publication_enabled":False,
            "cms_modified":False,
            "counts":{"production_candidates":len(productions),"source_links":sum(len(p["source_links"]) for p in productions)},
            "productions":productions}
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output["counts"],ensure_ascii=False))

if __name__=="__main__":
    main()

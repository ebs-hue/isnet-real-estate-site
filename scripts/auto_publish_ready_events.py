#!/usr/bin/env python3
"""Server-side event QA + automatic publishing after media enrichment.

Runs without a browser. Reads the city event datasets, overlays any CMS record,
applies deterministic publication gates, and upserts only QA-passed events.
Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
CITIES = {
    "ashdod": ROOT / "events-preview" / "ashdod" / "data" / "events.json",
    "rishon-lezion": ROOT / "events-preview" / "rishon-lezion" / "data" / "events.json",
}

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
if not SUPABASE_URL or not SERVICE_KEY:
    print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not configured.", file=sys.stderr)
    raise SystemExit(2)

SESSION = requests.Session()
SESSION.headers.update({
    "apikey": SERVICE_KEY,
    "Content-Type": "application/json",
})
# Legacy service_role keys are JWTs and may be used as Bearer tokens.
# New Supabase secret keys (sb_secret_...) authenticate through the apikey header
# and must not be sent as Authorization: Bearer.
if SERVICE_KEY.count(".") == 2 and not SERVICE_KEY.startswith("sb_secret_"):
    SESSION.headers["Authorization"] = f"Bearer {SERVICE_KEY}"
TODAY = date.today().isoformat()

def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).lower()
    value = re.sub(r"[^0-9a-zא-ת]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    value = re.sub(r"[\"'״׳]", "", value)
    value = re.sub(r"[^0-9a-zא-ת]+", "-", value)
    return value.strip("-")[:90]

def stable_slug(event: dict) -> str:
    if event.get("seo_slug"):
        return slugify(event["seo_slug"])
    base = slugify(event.get("title")) or "event"
    suffix = re.sub(r"[^a-zA-Z0-9]+", "", str(event.get("event_id") or ""))[-8:].lower()
    return f"{base}-{suffix}" if suffix else base

def source_confidence(event: dict) -> str:
    sources = event.get("sources") or []
    src = (sources[0].get("name") if sources and isinstance(sources[0], dict) else "") or event.get("purchase_source") or ""
    if not src:
        return "low"
    if re.search(r"municip|עיר|היכל|מוזיא|תרבות|official|ticket|event", src, re.I):
        return "high"
    return "medium"

def duplicate_keys(events: list[dict]) -> set[str]:
    groups = {}
    for e in events:
        key = "|".join([
            e["_citySlug"],
            str(e.get("start_date") or ""),
            norm(e.get("title")),
            norm(e.get("venue")),
        ])
        groups.setdefault(key, []).append(e)
    out = set()
    for group in groups.values():
        if len(group) > 1:
            out.update(f'{e["_citySlug"]}:{e.get("event_id")}' for e in group)
    return out

def evaluate(event: dict, dupes: set[str]) -> dict:
    blockers, warnings = [], []
    image = event.get("thumbnail_url") or event.get("image_url")
    image_ok = bool(image and event.get("image_publishable") is True and event.get("image_verified") is True)
    description = (
        event.get("long_description")
        or event.get("short_pitch")
        or event.get("series_description")
        or event.get("description")
        or ""
    )
    if not event.get("title"):
        blockers.append("missing_title")
    if not event.get("start_date"):
        blockers.append("missing_date")
    if not event.get("venue"):
        warnings.append("missing_venue")
    if not event.get("category"):
        warnings.append("missing_category")
    if not description:
        warnings.append("missing_content")
    if not image:
        blockers.append("missing_image")
    elif not image_ok:
        blockers.append("unverified_image")
    if not (event.get("purchase_url") or event.get("ticket_url") or event.get("purchase_phone")):
        warnings.append("missing_action")
    if f'{event["_citySlug"]}:{event.get("event_id")}' in dupes:
        blockers.append("possible_duplicate")
    confidence = source_confidence(event)
    if confidence == "low":
        warnings.append("weak_source")
    score = max(0, min(100, 100 - 22 * len(blockers) - 8 * len(warnings)))
    return {
        "ready": not blockers and score >= 72,
        "score": score,
        "confidence": confidence,
        "blockers": blockers,
        "warnings": warnings,
    }

def get_cms_records() -> dict[str, dict]:
    url = f"{SUPABASE_URL}/rest/v1/cms_event_records"
    params = {"select": "*"}
    r = SESSION.get(url, params=params, timeout=30)
    if not r.ok:
        body=(r.text or "")[:1000]
        print(f"SUPABASE READ ERROR status={r.status_code} body={body}", file=sys.stderr)
    r.raise_for_status()
    rows = r.json()
    return {f'{row["city_slug"]}:{row["event_id"]}': row for row in rows}

def load_events(cms: dict[str, dict]) -> list[dict]:
    out = []
    for city, path in CITIES.items():
        doc = json.loads(path.read_text(encoding="utf-8"))
        for base in doc.get("events", []):
            if str(base.get("start_date") or "") < TODAY:
                continue
            key = f'{city}:{base.get("event_id")}'
            row = cms.get(key)
            payload = row.get("payload") if row and isinstance(row.get("payload"), dict) else {}
            merged = {**base, **payload}
            merged["_citySlug"] = city
            merged["_recordType"] = row.get("record_type") if row else "override"
            merged["_alreadyPublished"] = bool(row and row.get("publication_status") == "published")
            if merged.get("status") in {"archived", "trashed", "hidden"}:
                continue
            out.append(merged)
    # Manual CMS events are not in the static city datasets.
    static_keys = {f'{e["_citySlug"]}:{e.get("event_id")}' for e in out}
    for key, row in cms.items():
        if row.get("record_type") != "manual" or key in static_keys:
            continue
        payload = row.get("payload") or {}
        if str(payload.get("start_date") or "") < TODAY:
            continue
        if payload.get("status") in {"archived", "trashed", "hidden"}:
            continue
        e = {**payload, "event_id": row["event_id"], "_citySlug": row["city_slug"],
             "_recordType": "manual", "_alreadyPublished": row.get("publication_status") == "published"}
        out.append(e)
    return out

def publish(event: dict, qa: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    slug = stable_slug(event)
    payload = {k: v for k, v in event.items() if not k.startswith("_")}
    payload.update({
        "seo_slug": slug,
        "status": "active",
        "publication_status": "published",
        "published_at": now,
        "public_path": f"/events/{slug}",
        "agent_qa_score": qa["score"],
        "agent_source_confidence": qa["confidence"],
        "agent_publish_decision": "auto_publish",
    })
    row = {
        "city_slug": event["_citySlug"],
        "event_id": event["event_id"],
        "record_type": event.get("_recordType") or "override",
        "payload": payload,
        "status": "active",
        "seo_slug": slug,
        "publication_status": "published",
        "published_at": now,
        "public_path": f"/events/{slug}",
        "updated_at": now,
    }
    url = f"{SUPABASE_URL}/rest/v1/cms_event_records"
    params = {"on_conflict": "city_slug,event_id"}
    headers = {"Prefer": "resolution=merge-duplicates,return=minimal"}
    r = SESSION.post(url, params=params, headers=headers, data=json.dumps(row, ensure_ascii=False).encode("utf-8"), timeout=30)
    r.raise_for_status()

def main() -> int:
    cms = get_cms_records()
    events = load_events(cms)
    dupes = duplicate_keys(events)
    checked = published = already = blocked = failed = 0
    reasons: dict[str, int] = {}

    for event in events:
        checked += 1
        qa = evaluate(event, dupes)
        if event.get("_alreadyPublished"):
            already += 1
            continue
        if not qa["ready"]:
            blocked += 1
            for reason in qa["blockers"]:
                reasons[reason] = reasons.get(reason, 0) + 1
            continue
        try:
            publish(event, qa)
            published += 1
        except Exception as exc:
            failed += 1
            print(f'PUBLISH FAILED {event.get("_citySlug")} {event.get("event_id")}: {exc}', file=sys.stderr)

    result = {
        "checked": checked,
        "published_now": published,
        "already_published": already,
        "blocked": blocked,
        "failed": failed,
        "blockers": reasons,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    print("AUTO PUBLISH RESULT")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())

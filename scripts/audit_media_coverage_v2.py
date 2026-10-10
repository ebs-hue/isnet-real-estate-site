"""Read-only image coverage audit for both ISNET city feeds.

No image is downloaded, published, or reclassified by this report.  Images
already imported from national listings remain untouched.  Catalog suggestions
are based only on explicitly linked event IDs, production/artist/venue IDs, or
category fallbacks, and require verified rights and a stored asset.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from media_catalog_v2 import choose_asset

ROOT = Path(__file__).resolve().parents[1]
CITIES = ("ashdod", "rishon-lezion")
CATALOG = ROOT / "events-preview/admin/data/media-catalog-v2.json"
OUT = ROOT / "events-preview/admin/data/media-coverage-v2.json"


def has_event_image(event: dict) -> bool:
    return bool(event.get("image_url") and event.get("image_verified") is True
                and event.get("image_publishable") is True)


def audit_city(events: list[dict], assets: list[dict], *, today: str) -> dict:
    counts = Counter()
    missing = []
    for event in events:
        if str(event.get("start_date") or "")[:10] < today or event.get("status") not in (None, "active"):
            continue
        counts["future_events"] += 1
        if has_event_image(event):
            counts["already_has_source_image"] += 1
            continue
        counts["missing_publishable_image"] += 1
        asset = choose_asset(assets, event, on_date=today)
        if asset:
            counts["eligible_catalog_suggestion"] += 1
        else:
            counts["no_eligible_catalog_asset"] += 1
        missing.append({
            "event_id": event.get("event_id"),
            "title": event.get("title"),
            "start_date": event.get("start_date"),
            "category": event.get("category"),
            "subcategory": event.get("subcategory"),
            "source": event.get("source"),
            "suggested_asset_id": asset.get("asset_id") if asset else None,
            "suggested_asset_type": asset.get("asset_type") if asset else None,
            "action": "review_before_publication" if asset else "collect_or_verify_media",
        })
    return {"counts": dict(counts), "missing": missing}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--today", default=date.today().isoformat())
    args = parser.parse_args()
    raw = json.loads(args.catalog.read_text(encoding="utf-8"))
    if not isinstance(raw.get("assets"), dict):
        raise ValueError("Catalog assets must be an object keyed by asset ID")
    assets = list(raw["assets"].values())
    cities = {}
    for city in CITIES:
        path = ROOT / "events-preview" / city / "data/events.json"
        feed = json.loads(path.read_text(encoding="utf-8"))
        cities[city] = audit_city(feed.get("events", []), assets, today=args.today)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "mode": "read_only", "cities": cities}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for city, data in cities.items():
        print(city, data["counts"])


if __name__ == "__main__":
    main()

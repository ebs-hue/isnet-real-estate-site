#!/usr/bin/env python3
"""Enrich event records from city-owned, officially verified institution registries.

Never infer an event venue from its organizer: Ofek tours can depart from
different places, and HTRL talks can be held outside HTRL itself.
Never override verified event-specific contacts with registry defaults.
Idempotent, one pass per city. No external calls and no fuzzy identity guesses.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "events-preview"
CITIES = ("ashdod", "rishon-lezion")


def norm(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"[\u0591-\u05c7]", "", text)
    text = text.translate(str.maketrans({"ך":"כ", "ם":"מ", "ן":"נ", "ף":"פ", "ץ":"צ"}))
    return re.sub(r"[^0-9a-zא-ת]+", " ", text).strip()


def institution_match(venue, institutions):
    """Verified venue only: exact normalized alias, or a long qualified phrase.

    We do not match event *titles*: 'יונתן גת מונארט' is a show title, not a venue.
    """
    n = norm(venue)
    if len(n) < 5 or n in ("אשדוד", "ראשון לציונ"):
        return None
    ranked = []
    for item in institutions:
        aliases = [item["name"], *(item.get("aliases") or [])]
        for raw in aliases:
            alias = norm(raw)
            if len(alias) < 5:
                continue
            if n == alias:
                ranked.append((2, len(alias), item))
            elif len(alias) >= 11 and (n.startswith(alias+" ") or n.endswith(" "+alias) or " "+alias+" " in " "+n+" "):
                ranked.append((1, len(alias), item))
    if not ranked:
        return None
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    # Equally convincing matches for different institutions are ambiguous.
    tied = [x for x in ranked if x[:2] == ranked[0][:2]]
    if len({x[2]["id"] for x in tied}) > 1:
        return None
    return ranked[0][2]


def operator_match(event, institutions):
    sources = {x.get("name") for x in event.get("sources", []) if isinstance(x, dict)}
    found = [item for item in institutions if item.get("kind") == "operator"
             and sources.intersection(item.get("source_names", []))]
    return found[0] if len(found) == 1 else None


def apply_registry(event, institutions):
    changed = 0
    op = operator_match(event, institutions)
    venue = institution_match(event.get("venue"), [x for x in institutions
                                                   if x.get("kind") == "venue"
                                                   or x.get("id") == "ofek_ashdod"
                                                   or x.get("id") == "htrl"])
    values = {}

    if op:
        values["operator_id"] = op["id"]
        values["operator_name"] = op["name"]
        if not event.get("organizer"):
            values["organizer"] = op["name"]
        if not event.get("contact_phone") and op.get("phone"):
            values["contact_phone"] = op["phone"]
        if not event.get("contact_email") and op.get("email"):
            values["contact_email"] = op["email"]
        if not event.get("organizer_url") and op.get("website"):
            values["organizer_url"] = op["website"]

    if venue:
        values["venue_institution_id"] = venue["id"]
        if not event.get("venue_phone") and venue.get("phone"):
            values["venue_phone"] = venue["phone"]
        if not event.get("venue_website") and venue.get("website"):
            values["venue_website"] = venue["website"]
        # Exact venue address is inherited only when no specific address exists.
        if not event.get("address") and venue.get("address"):
            values["address"] = venue["address"]
            values["address_source"] = "verified_institution_registry"
        if not op and not event.get("contact_phone") and venue.get("phone"):
            values["contact_phone"] = venue["phone"]
        if not op and not event.get("contact_email") and venue.get("email"):
            values["contact_email"] = venue["email"]

    # Never replace source-derived values once they exist.
    for field, value in values.items():
        if field in ("operator_id", "operator_name", "venue_institution_id"):
            if event.get(field) and event[field] != value:
                continue
        elif event.get(field):
            continue
        if event.get(field) != value:
            event[field] = value
            changed += 1
    return changed


def run():
    bad = 0
    for city in CITIES:
        registry_path = BASE / city / "data/institutions.json"
        events_path = BASE / city / "data/events.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        items = registry["institutions"]
        ids = [x["id"] for x in items]
        assert len(ids) == len(set(ids)), f"Duplicate institution ids in {city}"
        payload = json.loads(events_path.read_text(encoding="utf-8"))
        changed = connected = 0
        for e in payload["events"]:
            d = apply_registry(e, items)
            if d:
                changed += 1
            if e.get("operator_id") or e.get("venue_institution_id"):
                connected += 1
        if changed:
            events_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(f"REGISTRY {city}: {len(items)} institutions, {connected}/{len(payload['events'])} linked events, {changed} updated rows",flush=True)
        if not items:
            bad += 1
    return bad


if __name__ == "__main__":
    sys.exit(run())

"""Shared event identity rules for every ISNET city.

Design informed by the open-source Agora (performance per occurrence) and
Community Calendar (source IDs and curated overrides) implementations.
This module is an original adaptation; no upstream source code is copied.
Keep presentation and collector-specific rules outside this module.
"""
from __future__ import annotations
import html
import re
import unicodedata


def canonical(value: object) -> str:
    text = unicodedata.normalize("NFKC", html.unescape(str(value or ""))).casefold()
    text = text.replace("״", '"').replace("׳", "'")
    return " ".join(re.findall(r"[\w\u0590-\u05ff]+", text, flags=re.UNICODE))


def protected(event: dict) -> bool:
    return any(event.get(k) is True for k in (
        "human_manual_override", "image_manual_override", "description_manual_override"
    ))


def occurrence_key(event: dict, city: str) -> tuple[str, str, str, str, str] | None:
    """Same title/time *at the same venue*. Never merge a different showtime."""
    title = canonical(event.get("title"))
    date = str(event.get("start_date") or "")[:10]
    time = str(event.get("start_time") or "")[:5]
    venue = canonical(event.get("venue"))
    if not (title and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)
            and re.fullmatch(r"\d{2}:\d{2}", time) and venue):
        return None
    return city, title, date, time, venue


def same_venue(left: object, right: object) -> bool:
    """Conservative: unknown or conflicting venues are NOT proof of identity."""
    a, b = canonical(left), canonical(right)
    return bool(a and b and a == b)


def duplicate_agent_ids(events: list[dict], city: str, today: str) -> set[str]:
    """Remove auto-created duplicate IDs only when identical venue is confirmed.

    Keep editorial locks; prefer a national board item, then a preexisting ID.
    """
    groups: dict[tuple, list[dict]] = {}
    for event in events:
        key = occurrence_key(event, city)
        if key and key[2] >= today:
            groups.setdefault(key, []).append(event)
    drop: set[str] = set()
    for group in groups.values():
        board = [e for e in group if e.get("source") == "national_stage_boards"]
        if not board:
            continue
        preferred = next(
            (e for e in board if not str(e.get("event_id") or "").startswith("board_")),
            board[0],
        )
        for e in group:
            event_id = str(e.get("event_id") or "")
            if e is preferred or protected(e):
                continue
            if e.get("source") == "national_stage_boards" or event_id.startswith(("auto_", "evt_", "board_")):
                if event_id:
                    drop.add(event_id)
    return drop

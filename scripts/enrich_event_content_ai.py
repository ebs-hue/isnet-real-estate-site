#!/usr/bin/env python3
"""AI content enrichment for future ISNET events that need media help.

Only events without a usable image/content context are considered. The agent
reads the recorded official event page, asks the model to summarize only what
the source supports, and creates an image brief derived from that content.
If the source is insufficient, content_ready_for_media remains false.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CITIES = {
    "ashdod": ROOT / "events-preview" / "ashdod" / "data" / "events.json",
    "rishon-lezion": ROOT / "events-preview" / "rishon-lezion" / "data" / "events.json",
}
REPORT = ROOT / "events-preview" / "content-enrichment-report.json"
API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL = os.getenv("OPENAI_EVENT_ENRICHMENT_MODEL", "gpt-5-mini").strip()
MAX_EVENTS = int(os.getenv("EVENT_ENRICHMENT_LIMIT", "80"))
UA = "ISNET-EventsContent/1.0 (editorial enrichment from recorded official sources)"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "he-IL,he;q=0.9,en;q=0.7"})

ALLOWED_HOST_HINTS = (
    "smarticket.co.il", "tickchak.co.il", "ironit.org.il", "ofek-ashdod.org.il",
    "htrl.co.il", "kotar-rishon-lezion.org.il", "rishonlezion.muni.il",
    "eventim.co.il", "isnet.co.il", "ashdodnet.com", "rishonet.com",
)

def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def existing_context(event):
    return clean_text(
        event.get("long_description")
        or event.get("short_pitch")
        or event.get("series_description")
        or event.get("description")
        or ""
    )

def image_is_usable(event):
    return bool(
        (event.get("thumbnail_url") or event.get("image_url"))
        and event.get("image_publishable") is True
        and event.get("image_verified") is True
    )

def needs_enrichment(event):
    """Every future event should receive editorial enrichment.

    Human/editorial content can explicitly opt out with content_locked=true.
    Bot-generated content is refreshed when missing or when its enrichment
    version is older than the current editorial pipeline.
    """
    if event.get("content_locked") is True:
        return False
    if event.get("content_origin") in {"manual", "editorial"} and existing_context(event):
        return False
    return event.get("content_enrichment_version") != 2

def source_urls(event):
    vals = []
    for key in ("detail_source_url", "ticket_url", "purchase_url"):
        u = clean_text(event.get(key))
        if u.startswith("https://"):
            vals.append(u)
    for src in event.get("sources") or []:
        if isinstance(src, dict):
            u = clean_text(src.get("url"))
            if u.startswith("https://"):
                vals.append(u)
    seen = set()
    out = []
    for u in vals:
        host = (urlparse(u).hostname or "").lower()
        if not host or not any(host == h or host.endswith("." + h) for h in ALLOWED_HOST_HINTS):
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:4]

def fetch_source_text(url):
    try:
        r = SESSION.get(url, timeout=18, allow_redirects=True)
        if r.status_code != 200 or "html" not in (r.headers.get("content-type") or "").lower():
            return ""
        if len(r.content) > 2_000_000:
            return ""
        host = (urlparse(r.url).hostname or "").lower()
        if not any(host == h or host.endswith("." + h) for h in ALLOWED_HOST_HINTS):
            return ""
        soup = BeautifulSoup(r.content, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        parts = []
        for sel in ("h1", "h2", "main", "article", ".content", ".event", ".description"):
            for node in soup.select(sel):
                text = clean_text(node.get_text(" ", strip=True))
                if 20 <= len(text) <= 8000:
                    parts.append(text)
        if not parts:
            parts = [clean_text(soup.get_text(" ", strip=True))]
        text = clean_text(" ".join(parts))
        return text[:12000]
    except requests.RequestException:
        return ""

def ask_model(event, source_text, source_url):
    instructions = """אתה עורך תוכן בכיר ברשת מקומונים ישראלית.
המטרה: להפוך כל רשומת אירוע גולמית לעמוד אירוע מקורי, ברור, שימושי ומעניין לקורא.

עקרונות חובה:
- השתמש רק בעובדות הנתמכות בנתוני האירוע ובטקסט המקור.
- אסור להמציא שמות, משתתפים, עלילה, מחירים, שעות, ציטוטים או פרטים.
- אין להעתיק ניסוחים ארוכים מהמקור; כתוב מחדש בעברית טבעית ומקורית.
- פתח בהסבר ברור מהו האירוע ולמה הוא עשוי לעניין את הקורא.
- הימנע מטקסט גנרי, מנופח או שיווקי מדי.
- כאשר המקור דל, כתוב טקסט קצר יותר ואל תשלים פרטים שלא ידועים.
- אם אין מספיק מידע כדי להסביר מהו האירוע, החזר content_ready_for_media=false.
- image_brief חייב לנבוע מהתוכן, להיות חזותי, קונקרטי וללא טקסט מוטמע.
- אין להשתמש בלוגו כתחליף לתמונת אירוע אלא אם הלוגו עצמו הוא נושא האירוע.
החזר JSON בלבד."""
    payload = {
        "event": {
            "title": event.get("title"),
            "city": event.get("city"),
            "date": event.get("start_date"),
            "time": event.get("start_time"),
            "venue": event.get("venue"),
            "category": event.get("category"),
            "organizer": event.get("organizer"),
        },
        "source_url": source_url,
        "source_text": source_text,
        "required_output": {
            "event_summary": "2-4 informative Hebrew sentences explaining what the event is",
            "short_pitch": "one concise, attractive but factual Hebrew paragraph",
            "long_description": "original Hebrew editorial description, usually 100-260 words when the source supports it",
            "event_type": "short Hebrew label",
            "participants": ["supported names only"],
            "target_audience": ["supported or safely inferable broad audience labels"],
            "visual_keywords": ["5-10 concrete visual concepts"],
            "image_brief": "one Hebrew paragraph describing a relevant cover image, without embedded text",
            "content_ready_for_media": True,
            "missing_information": ["unsupported details that remain unknown"],
        },
    }
    r = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "instructions": instructions,
            "input": json.dumps(payload, ensure_ascii=False),
            "text": {"format": {"type": "json_object"}},
        },
        timeout=90,
    )
    r.raise_for_status()
    obj = r.json()
    text = clean_text(obj.get("output_text"))
    if not text:
        for item in obj.get("output") or []:
            for part in item.get("content") or []:
                if part.get("type") in ("output_text", "text") and part.get("text"):
                    text = part["text"]
                    break
            if text:
                break
    return json.loads(text)

def apply_result(event, result, source_url):
    ready = result.get("content_ready_for_media") is True
    event["content_ready_for_media"] = ready
    event["content_enrichment_source"] = source_url
    event["content_enrichment_model"] = MODEL
    event["content_enrichment_version"] = 2
    event["content_origin"] = "ai_enriched"
    event["content_enriched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    event["missing_information"] = result.get("missing_information") or []
    if not ready:
        event["media_status"] = "waiting_for_content"
        return False
    for key in (
        "event_summary", "short_pitch", "long_description", "event_type",
        "participants", "target_audience", "visual_keywords", "image_brief",
    ):
        value = result.get(key)
        if value not in (None, "", []):
            event[key] = value
    event["media_status"] = "ready_for_media"
    return True

def main():
    if not API_KEY:
        print("OPENAI_API_KEY is not configured; content enrichment skipped.")
        return 0

    today = date.today().isoformat()
    checked = enriched = insufficient = fetch_failed = model_failed = 0
    rows = []

    for slug, path in CITIES.items():
        doc = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for event in doc.get("events") or []:
            if checked >= MAX_EVENTS:
                break
            if str(event.get("start_date") or "") < today or not needs_enrichment(event):
                continue
            checked += 1
            urls = source_urls(event)
            source_url = ""
            source_text = ""
            for u in urls:
                source_text = fetch_source_text(u)
                if len(source_text) >= 180:
                    source_url = u
                    break
            if len(source_text) < 180:
                event["content_ready_for_media"] = False
                event["media_status"] = "waiting_for_content"
                event["content_enrichment_status"] = "source_text_insufficient"
                fetch_failed += 1
                changed = True
                rows.append({"city": slug, "event_id": event.get("event_id"), "title": event.get("title"), "status": "source_text_insufficient"})
                continue
            try:
                result = ask_model(event, source_text, source_url)
                ok = apply_result(event, result, source_url)
                event["content_enrichment_status"] = "ready" if ok else "insufficient"
                enriched += int(ok)
                insufficient += int(not ok)
                changed = True
                rows.append({"city": slug, "event_id": event.get("event_id"), "title": event.get("title"), "status": event["content_enrichment_status"]})
            except Exception as exc:
                model_failed += 1
                event["content_enrichment_status"] = "model_error"
                rows.append({"city": slug, "event_id": event.get("event_id"), "title": event.get("title"), "status": "model_error", "error": type(exc).__name__})
                print("MODEL ERROR", slug, event.get("event_id"), type(exc).__name__, flush=True)
            time.sleep(0.15)
        if changed:
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": MODEL,
        "checked": checked,
        "enriched": enriched,
        "insufficient": insufficient,
        "source_text_insufficient": fetch_failed,
        "model_failed": model_failed,
        "events": rows,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CONTENT ENRICHMENT", json.dumps({k:v for k,v in report.items() if k != "events"}, ensure_ascii=False), flush=True)
    return 0 if model_failed == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())

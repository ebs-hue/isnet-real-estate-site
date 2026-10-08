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
from datetime import date, timedelta
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
CONTENT_ENRICHMENT_VERSION = 8
MAX_EVENTS = int(os.getenv("EVENT_ENRICHMENT_LIMIT", "12"))
TARGET_CITY = os.getenv("EVENT_ENRICHMENT_CITY", "ashdod").strip()
EVENT_HORIZON_MONTHS = 5


def add_months(d, months):
    import calendar
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
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
    retry_after = str(event.get("content_enrichment_retry_after") or "")
    if (
        event.get("content_enrichment_status") in {"source_text_insufficient", "model_error"}
        and event.get("content_enrichment_version") == CONTENT_ENRICHMENT_VERSION
        and retry_after > date.today().isoformat()
    ):
        return False
    return event.get("content_enrichment_version") != CONTENT_ENRICHMENT_VERSION

def source_urls(event):
    vals = []
    for key in ("detail_source_url", "image_source", "content_enrichment_source", "ticket_url", "purchase_url"):
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

def ask_model(event, source_text, source_url, require_web_search=False):
    instructions = """אתה עורך תרבות ואירועים בכיר ברשת מקומונים ישראלית.
המטרה: להפוך כל רשומת אירוע גולמית לעמוד תוכן מקורי, קולח, ברור ושימושי לקורא שמתלבט אם להגיע.

עיקרון העל:
קודם להבין מהו האירוע עצמו כיצירה, מופע, הצגה, הרצאה, סדנה, תערוכה או פעילות. רק אחר כך לחבר אליו את פרטי ההופעה המקומית כמו עיר, אולם, תאריך ושעה.
אל תכתוב תוכן כאילו האירוע "שייך" לעיר מסוימת אם מדובר במופע נודד, הצגה רצה, הרצאה חוזרת או הפקה שמופיעה במקומות שונים.

מה חשוב לקורא:
- במה האירוע עוסק בפועל.
- מה הסיפור, הנושא, הקונספט או החוויה.
- מה מיוחד או מעניין בו לעומת אירועים דומים.
- מי היוצרים, השחקנים, האמנים, המרצים או המשתתפים המרכזיים, כאשר הדבר נתמך במקורות.
- למי האירוע מתאים.
- מידע שימושי אמיתי שעוזר להבין אם כדאי להגיע.
- רק בסוף, ובמידת הצורך, לחבר את פרטי המועד המקומי: מקום, תאריך, שעה ורכישה.

כללי מחקר וכתיבה:
- השתמש רק בעובדות הנתמכות בנתוני האירוע ובמקורות אמינים ורלוונטיים.
- כאשר המקור הראשוני דל, יש ללמוד את האירוע ממקורות טובים נוספים שמדברים על אותה יצירה/הפקה/הרצאה, ולא להסתפק בלוח האירועים.
- יש להעדיף מקורות רשמיים של ההפקה, התיאטרון, האמן, המרצה, המפיק או גוף תרבות מוכר; אחריהם מקורות תקשורת אמינים וביקורות.
- אין להוסיף את שם העיר לשאילתת המחקר אלא אם הוא נחוץ לזיהוי חד-משמעי של האירוע.
- כן להשתמש בסוג האירוע כדי לדייק את החיפוש: למשל "הצגת תיאטרון + שם", "הרצאה + שם", "מופע סטנדאפ + שם", "הצגת ילדים + שם".
- אם שם האירוע כללי או עמום, השתמש גם בשם האמן/המרצה/ההפקה כדי למנוע בלבול.
- אסור להמציא שמות, משתתפים, עלילה, מחירים, שעות, ציטוטים או פרטים.
- אסור להעתיק מהמקורות משפטים או פסקאות מילה במילה, גם אם המקור רשמי.
- קרא את המקורות, הפק מהם את העובדות, ואז כתוב מחדש תוכן מקורי משלך בעברית טבעית, עיתונאית ונעימה.
- אל תשמר מבנה משפטים, סדר פסקאות או ניסוחים ייחודיים של המקור כאשר אפשר לנסח את העובדה באופן עצמאי.
- ציטוט ישיר מותר רק אם הוא חיוני ומיוחס בבירור, ובכל מקרה קצר מאוד.
- התוכן צריך להרגיש כמו כתיבה מקורית של מערכת ISNET ולא כמו תקציר מועתק או פרפראזה צמודה.
- אסור להכניס לתוך event_summary, short_pitch, long_description, seo_title או seo_description כתובות URL, קישורי Markdown, שמות דומיין בסוגריים, סימוני ציטוט או אסמכתאות בסגנון [מקור](https://...), ([domain](https://...)) או utm_source=openai.
- המקורות נועדו למחקר פנימי בלבד. הקורא באתר צריך לראות טקסט מערכתי נקי, ללא אסמכתאות טכניות בתוך הפסקאות.
- אל תכתוב טקסט גנרי שאפשר להדביק על כל אירוע.
- אין צורך לנפח: עדיף טקסט מדויק, מעניין וקולח על פני מלל ארוך.
- אם המידע עדיין לא מספיק כדי להבין מהו האירוע, החזר content_ready_for_media=false.
- image_brief חייב לנבוע מהתוכן המהותי של האירוע, לא מהמיקום או מהקטגוריה בלבד.
- אין להשתמש בלוגו כתחליף לתמונת אירוע אלא אם הלוגו עצמו הוא נושא האירוע.
החזר JSON בלבד."""
    category_search_labels = {
        "theatre": "הצגת תיאטרון",
        "kids": "הצגת ילדים",
        "music": "מופע מוזיקה",
        "standup": "מופע סטנדאפ",
        "lecture": "הרצאה",
        "exhibition": "תערוכה",
        "workshop": "סדנה",
        "tour": "סיור",
        "festival": "פסטיבל",
        "cinema": "סרט",
        "sport": "אירוע ספורט",
    }
    event_type_query = category_search_labels.get(event.get("category"), "אירוע")
    research_query = " ".join(x for x in [
        event_type_query,
        clean_text(event.get("title")),
        clean_text(event.get("artist_name") or event.get("performer") or event.get("speaker")),
        clean_text(event.get("production_name") or event.get("series_name")),
    ] if x).strip()

    payload = {
        "research_query": research_query,
        "research_rules": [
            "חפש קודם לפי סוג האירוע + שם האירוע",
            "הוסף אמן/מרצה/הפקה אם הדבר עוזר לזהות את האירוע",
            "אל תוסיף עיר או אולם כברירת מחדל; הם פרטי המועד המקומי ולא זהות היצירה",
            "העדף מקורות רשמיים של ההפקה/האמן/התיאטרון/המרצה ואחריהם מקורות תקשורת אמינים",
            "ודא שהמקורות מתייחסים לאותה יצירה ולא לאירוע אחר בעל שם דומה",
        ],
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
            "event_summary": "2-4 informative Hebrew sentences that explain the essence of the event itself, not merely when and where it happens",
            "short_pitch": "45-75 Hebrew words: concise, attractive and factual; explain what the audience will experience and why it may interest them",
            "long_description": "120-220 Hebrew words: original editorial description focused on subject/story/concept, distinguishing qualities, key participants and audience fit; local venue/date details should be secondary",
            "event_type": "short Hebrew label",
            "participants": ["supported names only"],
            "target_audience": ["supported or safely inferable broad audience labels"],
            "visual_keywords": ["5-10 concrete visual concepts"],
            "image_brief": "one Hebrew paragraph describing what a genuinely relevant cover image must show, without embedded text",
            "image_subject_type": "one of: event_poster, artist_or_speaker, production_or_book, program_or_institution, topical_fallback",
            "image_search_queries": ["2-4 precise search phrases ordered from strongest to weakest; prefer exact event/artist/production identity over generic category terms"],
            "seo_title": "concise factual Hebrew Google title, usually up to 60 characters",
            "seo_description": "useful factual Hebrew meta description, usually 120-160 characters",
            "content_ready_for_media": True,
            "missing_information": ["unsupported details that remain unknown"],
        },
    }
    request_body = {
        "model": MODEL,
        "instructions": instructions,
        "input": "Return valid JSON only. Use web search when the supplied source text is insufficient or when additional reliable context is needed to understand the event.\n" + json.dumps(payload, ensure_ascii=False),
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "tool_choice": "required" if require_web_search else "auto",
    }
    r = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=request_body,
        timeout=120,
    )
    if not r.ok:
        body = (r.text or "")[:1600]
        raise RuntimeError(f"OpenAI API {r.status_code}: {body}")
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

def sanitize_editorial_text(value):
    """Remove research citations/URLs that must never leak into published editorial copy."""
    text = clean_text(value)
    if not text:
        return text
    # Normalize common backslash-escaped markdown artifacts returned by web-search output.
    text = text.replace('\\(', '(').replace('\\)', ')').replace('\\_', '_').replace('\\:', ':').replace('\\/', '/')
    # Markdown links: [label](https://example.com/...)
    text = re.sub(r'\[([^\]]+)\]\(\s*https?://[^)]+\)', r'\1', text)
    # Citation wrappers such as ([domain](https://...)) or ([domain]).
    text = re.sub(r'\(\s*\[([^\]]+)\]\(\s*https?://[^)]+\)\s*\)', '', text)
    text = re.sub(r'\(\s*\[([^\]]+)\]\s*\)', '', text)
    # Any remaining source-domain label immediately followed by a URL.
    text = re.sub(r'\[?(?:www\.)?[A-Za-z0-9.-]+\.(?:co\.il|com|org|net|il)\]?\s*\(?\s*https?://[^)\s]+\)?', '', text)
    # Raw URLs, including query strings.
    text = re.sub(r'https?://[^\s)]+', '', text)
    # Common source-only parentheticals such as "(assafitzhaki.com)".
    text = re.sub(r'\(\s*(?:www\.)?[A-Za-z0-9.-]+\.(?:co\.il|com|org|net|il)\s*\)', '', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    return clean_text(text)


def apply_result(event, result, source_url):
    ready = result.get("content_ready_for_media") is True
    event["content_ready_for_media"] = ready
    event["content_enrichment_source"] = source_url
    event["content_enrichment_model"] = MODEL
    event["content_enrichment_version"] = CONTENT_ENRICHMENT_VERSION
    event["content_origin"] = "ai_enriched"
    event["content_enriched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    event["missing_information"] = result.get("missing_information") or []
    if not ready:
        event["media_status"] = "waiting_for_content"
        return False
    for key in (
        "event_summary", "short_pitch", "long_description", "event_type",
        "participants", "target_audience", "visual_keywords", "image_brief",
        "image_subject_type", "image_search_queries",
        "seo_title", "seo_description",
    ):
        value = result.get(key)
        if value not in (None, "", []):
            if key in {"event_summary", "short_pitch", "long_description", "seo_title", "seo_description", "image_brief"}:
                value = sanitize_editorial_text(value)
            event[key] = value
    event["media_status"] = "ready_for_media"
    return True

def main():
    if not API_KEY:
        print("OPENAI_API_KEY is not configured; content enrichment skipped.")
        return 0

    today_date = date.today()
    today = today_date.isoformat()
    horizon_end = add_months(today_date, EVENT_HORIZON_MONTHS).isoformat()
    checked = enriched = insufficient = fetch_failed = model_failed = 0
    rows = []

    city_items = CITIES.items() if TARGET_CITY in {"", "all"} else [(TARGET_CITY, CITIES[TARGET_CITY])]
    for slug, path in city_items:
        doc = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for event in doc.get("events") or []:
            if checked >= MAX_EVENTS:
                break
            event_date = str(event.get("start_date") or "")
            if event_date < today or event_date > horizon_end or not needs_enrichment(event):
                continue
            checked += 1
            urls = source_urls(event)
            source_url = clean_text(event.get("detail_source_url") or event.get("content_enrichment_source") or "")
            source_text = clean_text(event.get("source_detail_text") or "")
            if len(source_text) < 180:
                for u in urls:
                    fetched = fetch_source_text(u)
                    if len(fetched) > len(source_text):
                        source_text = fetched
                        source_url = u
                    if len(source_text) >= 180:
                        break
            require_web_search = len(source_text) < 180
            try:
                result = None
                last_exc = None
                for attempt in range(1, 4):
                    try:
                        result = ask_model(event, source_text, source_url, require_web_search=require_web_search)
                        break
                    except Exception as exc:
                        last_exc = exc
                        print("MODEL RETRY", slug, event.get("event_id"), attempt, clean_text(str(exc))[:400], flush=True)
                        time.sleep(2 * attempt)
                if result is None:
                    raise last_exc or RuntimeError("model request failed")
                ok = apply_result(event, result, source_url)
                event["content_enrichment_status"] = "ready" if ok else "insufficient"
                if not ok:
                    event["content_enrichment_retry_after"] = (date.today() + timedelta(days=1)).isoformat()
                enriched += int(ok)
                insufficient += int(not ok)
                changed = True
                rows.append({"city": slug, "event_id": event.get("event_id"), "title": event.get("title"), "status": event["content_enrichment_status"]})
            except Exception as exc:
                model_failed += 1
                event["content_enrichment_status"] = "model_error"
                event["content_enrichment_version"] = CONTENT_ENRICHMENT_VERSION
                event["content_enrichment_retry_after"] = (date.today() + timedelta(days=1)).isoformat()
                err = clean_text(str(exc))[:1200]
                rows.append({"city": slug, "event_id": event.get("event_id"), "title": event.get("title"), "status": "model_error", "error": err})
                print("MODEL ERROR - deferred", slug, event.get("event_id"), err, flush=True)
                changed = True
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
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

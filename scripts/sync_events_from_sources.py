#!/usr/bin/env python3
"""ISNET event intake: cautious, observable, twice-daily event discovery.

Public event calendars only; no authentication/CAPTCHA bypass, no guessing dates.
Never delete records because an event disappears from a listing. All city-specific
data remains isolated. Report every source, including unsupported/failed sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "events-preview"
REPORT = BASE / "source-sync-report.json"
UA = "ISNET-Events/1.0 (automated public event calendar reader; ISNET)"
HEADERS = {"User-Agent": UA, "Accept-Language": "he-IL,he;q=0.9,en;q=0.7"}
MONTHS = {
    "ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4, "מאי": 5, "יוני": 6,
    "יולי": 7, "אוגוסט": 8, "ספטמבר": 9, "ספט": 9, "אוקטובר": 10,
    "נובמבר": 11, "דצמבר": 12,
}
SOURCES = {
    "ashdod": [
        {"name": "ashdod_smarticket", "url": "https://ashdod.smarticket.co.il/", "parser": "smarticket",
         "venue": "אשדוד", "source_type": "ticketing"},
        {"name": "mishkan_smarticket", "url": "https://mishkan-ashdod.smarticket.co.il/", "parser": "smarticket",
         "venue": "המשכן לאמנויות הבמה אשדוד", "source_type": "official"},
        {"name": "tickchak_ashdod", "url": "https://live.tickchak.co.il/ashdod", "parser": "generic",
         "venue": "אשדוד", "source_type": "secondary"},
        # Sports calendars require independent fixture-level validation; not inferred
        # from an unrelated public events listing.
    ],
    "rishon-lezion": [
        {"name": "htrl", "url": "https://htrl.co.il/לוח-שנה/", "parser": "htrl",
         "venue": "היכל התרבות מאיר ניצן", "source_type": "official"},
        {"name": "yama", "url": "https://yama.smarticket.co.il/", "parser": "smarticket",
         "venue": "מוזיאון אגם", "source_type": "official"},
        {"name": "kotar_rishon", "url": "https://www.kotar-rishon-lezion.org.il/events-category/eventsactivities/",
         "parser": "kotar", "venue": "רשת הספריות ראשון לציון", "source_type": "official"},
        {"name": "RIZONE+", "url": "https://club.rishonlezion.muni.il/", "parser": "generic",
         "venue": "ראשון לציון", "source_type": "official"},
        {"name": "Eventim", "url": "https://www.eventim.co.il/", "parser": "generic",
         "venue": "ראשון לציון", "source_type": "secondary"},
    ],
}
CITY_LABELS = {"ashdod": "אשדוד", "rishon-lezion": "ראשון לציון"}
DAY_DOT = re.compile(r"^(\d{1,2})[./](\d{1,2})[./](\d{2}|\d{4})$")
HEBREW_DATE = re.compile(r"(?:ביום\s+)?(?:יום\s+)?(?:ראשון|שני|שלישי|רביעי|חמישי|שישי|שבת)?\s*,?\s*(\d{1,2})\s+([א-ת״']+)\s+(\d{4})")
HOUR = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b")
BAD_TITLES = ("פרטים נוספים", "רכישה", "לוח שנה", "כניסה לאתר", "לוח אירועים", "הצג עוד", "more", "קרא עוד")
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def text_norm(value):
    txt = unicodedata.normalize("NFKC", str(value or "")).lower()
    txt = re.sub(r"[\u0591-\u05c7]", "", txt)
    txt = txt.replace("–", "-").replace("—", "-").replace("־", "-")
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zא-ת]+", " ", txt)).strip()


def iso_dmy(match):
    day, month, year = map(int, match.groups())
    if year < 100:
        year += 2000
    return date(year, month, day).isoformat()


def iso_hebrew(match):
    day, month, year = match.groups()
    return date(int(year), MONTHS[month], int(day)).isoformat()


def valid_title(title):
    title = re.sub(r"\s+", " ", title or "").strip()
    return (3 <= len(title) <= 155 and title not in BAD_TITLES and
            not any(x in title for x in ("פרטים נוספים", "הכרטיסים אזלו", "הרשמה לניוזלטר")))


def choose_category(title, venue):
    s = text_norm(f"{title} {venue}")
    if any(x in s for x in ("ילדים", "ילדות", "קטנטנים", "הצגה לילדים", "שעת סיפור", "אגדה", "סינדרלה", "כראמל")):
        return "kids"
    if any(x in s for x in ("סטנדאפ", "קומדיה", "מופע קומי", "מצחיק")):
        return "standup"
    if any(x in s for x in ("תערוכה", "גלריה", "מוזיאון", "אמנות")):
        return "exhibition"
    if any(x in s for x in ("הרצאה", "כנס", "מפגש", "שיחה")):
        return "lecture"
    if any(x in s for x in ("סדנה", "סדנת", "הפעלה", "יצירה")):
        return "workshop"
    if any(x in s for x in ("מחול", "מחזמר", "תיאטרון", "הצגה", "אופרה")):
        return "theatre"
    if any(x in s for x in ("מוזיקה", "מופע", "תזמורת", "זמר", "קונצרט", "הופעה")):
        return "music"
    return "other"


def safe_url(url, origin, allow_external=False):
    if not url:
        return ""
    u = urljoin(origin, url)
    p = urlsplit(u)
    if p.scheme != "https" or not p.hostname:
        return ""
    if not allow_external and p.hostname.lower() != urlsplit(origin).hostname.lower():
        return ""
    return u


def fetch_once(source):
    url = source["url"]
    try:
        r = SESSION.get(url, timeout=25, allow_redirects=True)
        if r.status_code in (401, 403, 429):
            return None, f"blocked_{r.status_code}"
        if r.status_code >= 400:
            return None, f"http_{r.status_code}"
        if not r.url.startswith("https://") or "text/html" not in r.headers.get("content-type", "").lower():
            return None, "unexpected_content_type"
        if len(r.content) > 5_000_000:
            return None, "response_too_large"
        return BeautifulSoup(r.content, "html.parser"), None
    except requests.RequestException as exc:
        return None, type(exc).__name__


def list_lines(soup):
    for el in soup(["script", "style", "noscript"]):
        el.decompose()
    return [x.strip() for x in soup.get_text("\n", strip=True).splitlines() if x.strip()]


def htrl_rows(soup, source):
    lines = list_lines(soup)
    found = []
    # The published calendar uses a title, dd.mm.yy, HH:MM, weekday and venue.
    # Unlike show directories, this is exact date-specific event evidence.
    for i in range(1, len(lines) - 2):
        m = DAY_DOT.fullmatch(lines[i])
        if not m or not HOUR.fullmatch(lines[i + 1]):
            continue
        title = lines[i-1].strip()
        if not valid_title(title):
            continue
        try:
            day = iso_dmy(m)
        except ValueError:
            continue
        venue = source["venue"]
        if i + 3 < len(lines) and "אודיטוריום" in lines[i+3]:
            venue = "אודיטוריום היכל התרבות ראשון לציון"
        found.append({"title": title, "start_date": day, "start_time": lines[i+1],
                      "venue": venue, "ticket_url": source["url"], "purchase_url": source["url"],
                      "quality_flags": ["automated_official_calendar"]})
    return found


def smarticket_rows(soup, source):
    found = []
    for a in soup.select("a[href]"):
        url = safe_url(a.get("href"), source["url"])
        if not url or url == source["url"]:
            continue
        text = a.get_text(" ", strip=True)
        if "פרטים נוספים" not in text or len(text) > 1600:
            continue
        dm = HEBREW_DATE.search(text)
        if not dm:
            continue
        try:
            d = iso_hebrew(dm)
        except (ValueError, KeyError):
            continue
        prefix = text.split("פרטים נוספים", 1)[0]
        prefix = re.sub(r"^\d{1,2}\s+([א-ת]+)\s+", "", prefix).strip()
        title = prefix
        if not valid_title(title):
            continue
        tm = HOUR.search(text[dm.end():])
        if not tm:
            continue
        # Card first time is start time, but not the next-price numeral.
        start = tm.group(0)
        after = text.split("פרטים נוספים", 1)[1]
        venue = source["venue"]
        tail = after[len(title):].strip() if after.startswith(title) else ""
        venue_segment = re.split(r"\bביום\b", tail, 1)[0].strip()
        if 3 <= len(venue_segment) <= 125:
            venue = venue_segment
        sold = "הכרטיסים אזלו" in text
        found.append({"title": title, "start_date": d, "start_time": start,
                      "venue": venue, "ticket_url": url, "purchase_url": url,
                      "ticket_status": "sold_out" if sold else "unknown",
                      "quality_flags": ["automated_official_listing"]})
    return found


def kotar_rows(soup, source):
    lines = list_lines(soup)
    found = []
    for i, line in enumerate(lines):
        m = DAY_DOT.fullmatch(line)
        if not m or len(m.group(3)) != 4:
            continue
        try:
            day = iso_dmy(m)
        except ValueError:
            continue
        chunk = lines[i+1:i+85]
        nextdate = next((j for j, x in enumerate(chunk) if DAY_DOT.fullmatch(x)), len(chunk))
        chunk = chunk[:nextdate]
        if not chunk:
            continue
        # This source emits a rendered PHP string debug line containing the exact event title.
        joined = "\n".join(chunk[:15])
        match = re.search(r'string\(\d+\)\s*"([^"\n]{3,140})"', joined)
        title = match.group(1).strip() if match else ""
        if not title:
            idx = next((k for k, x in enumerate(chunk) if x == "גילאים:"), -1)
            title = chunk[idx-1] if idx > 0 else ""
        if not valid_title(title):
            continue
        start = None
        try:
            ix = chunk.index("שעות:")
            times = HOUR.findall(" ".join(chunk[ix+1:ix+4]))
            if times:
                tokens = HOUR.finditer(" ".join(chunk[ix+1:ix+4]))
                hhmm = [x.group(0) for x in tokens]
                # Right-to-left text extraction sometimes reverses displayed time spans.
                start = min(hhmm)
        except ValueError:
            pass
        if not start:
            continue
        venue = source["venue"]
        try:
            ix = chunk.index("מיקום:")
            value = chunk[ix+1].strip()
            if 5 <= len(value) <= 105 and "http" not in value:
                venue = value
        except (ValueError, IndexError):
            pass
        found.append({"title": title, "start_date": day, "start_time": start,
                      "venue": venue, "ticket_url": source["url"], "purchase_url": source["url"],
                      "quality_flags": ["automated_official_listing"]})
    return found


def generic_jsonld_rows(soup, source):
    found = []
    def walk(obj):
        if isinstance(obj, list):
            for item in obj:
                yield from walk(item)
        if isinstance(obj, dict):
            kind = obj.get("@type", "")
            if ("Event" in kind if isinstance(kind, str) else "Event" in kind if isinstance(kind, list) else False):
                yield obj
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    yield from walk(value)
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            parsed = json.loads(node.string or node.get_text())
        except (ValueError, TypeError):
            continue
        for entry in walk(parsed):
            title = entry.get("name", "")
            start = entry.get("startDate", "")
            if not valid_title(title) or not isinstance(start, str):
                continue
            try:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                d = dt.date().isoformat()
                t = dt.strftime("%H:%M") if "T" in start else None
            except ValueError:
                continue
            if not t:
                continue
            loc = entry.get("location", {})
            if isinstance(loc, list):
                loc = loc[0] if loc else {}
            name = loc.get("name", "") if isinstance(loc, dict) else ""
            event_url = safe_url(entry.get("url", ""), source["url"])
            found.append({"title": title, "start_date": d, "start_time": t,
                          "venue": name or source["venue"],
                          "ticket_url": event_url or source["url"],
                          "purchase_url": event_url or source["url"],
                          "quality_flags": ["automated_structured_event"]})
    return found


def source_rows(soup, source):
    parser = source["parser"]
    structured = generic_jsonld_rows(soup, source)
    if parser == "htrl":
        return htrl_rows(soup, source) + structured
    if parser == "smarticket":
        return smarticket_rows(soup, source) + structured
    if parser == "kotar":
        return kotar_rows(soup, source) + structured
    return structured


def event_key(obj):
    return (text_norm(obj.get("title")), obj.get("start_date") or "",
            obj.get("start_time") or "")


def existing_match(old, incoming, srcname):
    # Preserve existing manually assigned IDs, descriptions, images, and verified corrections.
    key = event_key(incoming)
    if key[0] and key[1]:
        for item in old:
            if item.get("city") != incoming.get("city"):
                continue
            if event_key(item) == key:
                return item
        # If we have exactly one candidate on that date with matching title,
        # prefer updating it rather than creating a duplicate when a time changed.
        candidates = [
            item for item in old
            if item.get("city") == incoming.get("city")
            and text_norm(item.get("title")) == key[0]
            and item.get("start_date") == key[1]
            and any(x.get("name") == srcname for x in item.get("sources", []))
        ]
        if len(candidates) == 1:
            return candidates[0]
    return None


def reuse_official_image(old, incoming, srcname):
    for item in old:
        if (text_norm(item.get("title")) == text_norm(incoming.get("title"))
            and any(s.get("name") == srcname for s in item.get("sources", []))
            and item.get("image_verified") is True
            and item.get("image_publishable") is True
            and item.get("image_url")):
            return {k: item.get(k) for k in (
                "image_url", "image_source", "image_credit", "image_origin_url",
                "image_publishable", "image_verified", "image_strategy",
                "thumbnail_url", "thumbnail_ready", "thumbnail_ratio", "thumbnail_strategy")}
    return {}


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def valid_row(obj, today):
    if not valid_title(obj.get("title", "")):
        return False
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", obj.get("start_time") or ""):
        return False
    try:
        day = date.fromisoformat(obj["start_date"])
    except (ValueError, TypeError, KeyError):
        return False
    return today - timedelta(days=1) <= day <= today + timedelta(days=370)


def merge(city_slug, specs, dry_run=False):
    data_path = BASE / city_slug / "data" / "events.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    events = payload["events"]
    label = CITY_LABELS[city_slug]
    today = date.today()
    now = iso_now()
    summary = {"city": label, "total_before": len(events), "sources": {},
               "new": 0, "updated": 0, "errors": []}
    for spec in specs:
        name = spec["name"]
        source_status = {"status": "unknown", "url": spec["url"], "discovered": 0,
                         "valid": 0, "new": 0, "updated": 0}
        summary["sources"][name] = source_status
        soup, err = fetch_once(spec)
        if err:
            source_status["status"] = "failed"
            source_status["error"] = err
            summary["errors"].append(f"{name}:{err}")
            continue
        rows = source_rows(soup, spec)
        source_status["discovered"] = len(rows)
        if not rows:
            debug_anchors = []
            for a in soup.select("a[href]"):
                t = a.get_text(" ", strip=True)
                if t and ("אוקטובר" in t or "2026" in t or "פרטים נוספים" in t or "כרטיס" in t):
                    debug_anchors.append({"text": t[:200], "href": (a.get("href") or "")[:180]})
                    if len(debug_anchors) >= 4:
                        break
            snippets = []
            for x in soup.stripped_strings:
                t = x.strip()
                if re.search(r"\d{1,2}[./]\d{1,2}[./]\d{4}|ביום\s+|אוקטובר", t) and len(t) < 240:
                    snippets.append(t[:180])
                    if len(snippets) >= 7:
                        break
            print("PARSER_DIAGNOSTICS", json.dumps({
                "source": name, "title": (soup.title.get_text(" ", strip=True)[:100] if soup.title else ""),
                "anchors": len(soup.select("a[href]")),
                "links": debug_anchors, "dated_text": snippets,
            }, ensure_ascii=False), flush=True)
            source_status["status"] = "no_parseable_events"
            summary["errors"].append(f"{name}:no_parseable_events")
            continue
        seen = set()
        for obj in rows[:600]:
            if not valid_row(obj, today):
                continue
            key = event_key(obj)
            if key in seen:
                continue
            seen.add(key)
            source_status["valid"] += 1
            incoming = {
                "city": label,
                "title": obj["title"].strip(),
                "description": None,
                "start_date": obj["start_date"],
                "end_date": None,
                "start_time": obj["start_time"],
                "end_time": None,
                "venue": obj["venue"] or spec["venue"],
                "address": None, "district": None,
                "category": choose_category(obj["title"], obj["venue"]),
                "audiences": [],
                "age_min": None, "age_max": None,
                "price_min_ils": None, "price_max_ils": None, "is_free": None,
                "ticket_status": obj.get("ticket_status", "unknown"),
                "ticket_url": obj.get("ticket_url") or spec["url"],
                "purchase_url": obj.get("purchase_url") or spec["url"],
                "purchase_phone": None, "purchase_source": "official_listing",
                "image_url": None, "image_source": None, "image_credit": None,
                "image_publishable": False, "image_verified": False,
                "image_origin_url": None, "thumbnail_url": None, "thumbnail_ready": False,
                "organizer": None, "duration_minutes": None,
                "sources": [{"name": name, "url": spec["url"],
                             "source_type": spec["source_type"], "observed_at": now}],
                "observed_at": now, "last_verified_at": now,
                "status": "active", "quality_flags": obj["quality_flags"],
            }
            match = existing_match(events, incoming, name)
            if match:
                changed = False
                # Only update date/time from the same official source. A missing
                # or changed price never silently destroys existing editorial data.
                for field in ("start_time",):
                    if match.get(field) != incoming[field]:
                        match[field] = incoming[field]
                        changed = True
                if match.get("ticket_status") != "sold_out" and incoming["ticket_status"] == "sold_out":
                    match["ticket_status"] = "sold_out"
                    changed = True
                if incoming["ticket_url"] != spec["url"] and match.get("ticket_url") in (None, spec["url"]):
                    match["ticket_url"] = incoming["ticket_url"]
                    match["purchase_url"] = incoming["ticket_url"]
                    changed = True
                if changed:
                    match["last_verified_at"] = now
                    match["observed_at"] = now
                    summary["updated"] += 1
                    source_status["updated"] += 1
                continue
            stable = "|".join([name, label, *key])
            incoming["event_id"] = f"auto_{city_slug[:2]}_" + hashlib.sha256(stable.encode()).hexdigest()[:20]
            incoming.update(reuse_official_image(events, incoming, name))
            events.append(incoming)
            summary["new"] += 1
            source_status["new"] += 1
        source_status["status"] = "ok" if source_status["valid"] else "no_valid_future_events"
        if not source_status["valid"]:
            summary["errors"].append(f"{name}:no_valid_future_events")
        print(f"{label} / {name}: {source_status['status']}, {source_status['valid']} valid, "
              f"{source_status['new']} new, {source_status['updated']} updated", flush=True)
        time.sleep(.3)

    events.sort(key=lambda e: (e.get("start_date") or "9999", e.get("start_time") or "99:99", e.get("title") or ""))
    summary["total_after"] = len(events)
    if summary["new"] or summary["updated"]:
        payload["generated_at"] = now
        payload.setdefault("stats", {})["events"] = len(events)
        future = [e["start_date"] for e in events if e.get("start_date", "") >= today.isoformat()]
        if future:
            payload["window"] = {"from": today.isoformat(), "to": max(future)}
        if not dry_run:
            data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--city", choices=[*SOURCES, "all"], default="all")
    args = parser.parse_args()
    report = {"run_at": iso_now(), "version": 1, "dry_run": args.dry_run, "cities": {},
              "note": "Missing listings never trigger automatic cancellations; source failures preserve data."}
    for slug in SOURCES:
        if args.city != "all" and args.city != slug:
            continue
        report["cities"][slug] = merge(slug, SOURCES[slug], args.dry_run)
    # The visibility of partial failures is mandatory. Do not pretend success when all
    # configured sources failed; only commit valid rows and an honest audit.
    if not args.dry_run:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SYNC_SUMMARY", json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if any(
        v.get("status") == "ok"
        for city in report["cities"].values()
        for v in city["sources"].values()
    ) else 2


if __name__ == "__main__":
    sys.exit(main())

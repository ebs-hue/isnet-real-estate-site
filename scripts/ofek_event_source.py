#!/usr/bin/env python3
"""Official Ofek Ashdod adult-education calendar reader.

Publishes only a future, dated individual event whose detail page confirms both
the civil date and the hour. One listing read and at most one read per item:
do not retry blocked pages or infer recurring-course dates from a brochure.
"""
from __future__ import annotations

import re
import time
from datetime import date, timedelta
from urllib.parse import parse_qs, urljoin, urlsplit

MAIN_DOMAIN = "www.ofek-ashdod.org.il"
DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
DAY_SUFFIX = re.compile(r"\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$")
TIME = re.compile(r"(?:^|\s)שעה\s*:?\s*((?:[01]?\d|2[0-3]):[0-5]\d)")
PRICE = re.compile(r"מחיר\s*:?\s*(?:₪\s*)?(\d{1,5}(?:[.,]\d{2})?)")
INVALID = ("חפש באתר", "ידיעון", "ארכיון", "קרא עוד")


def iso_date(match):
    dd, mm, yyyy = (int(x) for x in match.groups())
    return date(yyyy, mm, dd).isoformat()


def safe_link(href, base):
    url = urljoin(base, href or "")
    u = urlsplit(url)
    if (u.scheme != "https" or u.hostname not in (MAIN_DOMAIN, "ofek-ashdod.org.il")
        or u.path != "/page.php"):
        return ""
    params = parse_qs(u.query)
    if params.get("type") != ["event"] or not params.get("id", [""])[0].isdigit():
        return ""
    # Prefer canonical direct link to avoid transient title slugs.
    return "https://www.ofek-ashdod.org.il/page.php?type=event&id=" + params["id"][0]


def classify(title, category):
    if category == "tour" or any(word in title for word in ("סיור", "טיול", "בעקבות", "טעימות")):
        return "tour"
    if any(word in title for word in ("סדנה", "סדנת", "יוגה", "ציור", "קורס")):
        return "workshop"
    if any(word in title for word in ("מופע", "מוזיקה", "קונצרט")):
        return "music"
    return "lecture"


def extract_ofek_events(first_soup, source, fetch_once, *, today=None, limit=80, sleep=.25):
    """Return validated rows using fetch_once({url:...}) for public pages only."""
    today = today or date.today()
    seen, listings = set(), []
    # Prefer explicit event categories before the mixed home calendar.
    pages = []
    for page in source.get("listing_pages", []):
        new_source = {**source, "url": page["url"]}
        doc, error = fetch_once(new_source)
        if doc is not None and not error:
            pages.append((page["url"], doc, page["category"]))
    pages.append((source["url"], first_soup, "lecture"))
    for origin, soup, category in pages:
        for link in soup.select("a[href]"):
            url = safe_link(link.get("href"), origin)
            if not url or url in seen:
                continue
            label = " ".join(link.stripped_strings)
            match = DAY_SUFFIX.search(label)
            if not match:
                continue
            try:
                start = date.fromisoformat(iso_date(match))
            except ValueError:
                continue
            if start < today - timedelta(days=1) or start > today + timedelta(days=370):
                continue
            title = DAY_SUFFIX.sub("", label).strip(" -\u200f\u200e")
            # Remove a duplicate date embedded at the end of source titles.
            title = re.sub(r"\s+\d{1,2}/\d{1,2}/\d{2,4}$", "", title).strip()
            if not 5 <= len(title) <= 145 or any(x in title for x in INVALID):
                continue
            seen.add(url)
            listings.append((url, title, start.isoformat(), category))
    found = []
    for url, title, expected_date, category in listings[:limit]:
        detail, error = fetch_once({**source, "url": url})
        if detail is None or error:
            continue
        plain = " ".join(detail.stripped_strings)
        civil = re.search(r"תאריך\s+לועזי\s*(?:יום\s+[\u0590-\u05ff]+\s*,?\s*)?(\d{1,2}/\d{1,2}/\d{4})", plain)
        clock = TIME.search(plain)
        if not civil or not clock:
            continue
        try:
            actual_date = iso_date(DATE.fullmatch(civil.group(1)))
        except (ValueError, AttributeError):
            continue
        if actual_date != expected_date:
            continue
        cat = classify(title, category)
        venue = ("יציאה לסיור מטעם קתדרת אופק, אשדוד" if cat == "tour"
                 else "קתדרת אופק להשכלת מבוגרים, אשדוד")
        # Monart and other named sites are used only when explicitly present.
        if "מונארט" in plain[:2400]:
            venue = "מרכז מונארט, אשדוד"
        price = PRICE.search(plain)
        amount = None
        if price:
            try:
                amount = int(round(float(price.group(1).replace(",", ""))))
            except ValueError:
                pass
        record = {
            "title": title, "start_date": actual_date, "start_time": clock.group(1),
            "venue": venue, "category": "seniors", "activity_type": cat,
            "audiences": ["seniors"], "organizer": 'הקתדרה העממית "אופק" אשדוד',
            "ticket_url": url, "purchase_url": url,
            "price_min_ils": amount, "price_max_ils": amount,
            "purchase_phone": "08-9238680",
            "quality_flags": ["official_ofek_ashdod", "date_and_time_verified"],
        }
        found.append(record)
        if sleep:
            time.sleep(sleep)
    print(f"Ofek Ashdod: {len(pages)} listings, {len(listings)} future candidates, "
          f"{len(found)} date/time verified.", flush=True)
    return found

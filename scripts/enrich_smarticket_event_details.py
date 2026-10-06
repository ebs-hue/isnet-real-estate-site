#!/usr/bin/env python3
"""Incremental public Smarticket detail reader for ISNET city events.

Use one ordinary HTTPS GET per candidate and never retry a blocked page in
the same run. Only fill verified source facts; do not invent contact numbers,
venue names, ticket availability, descriptions or organizers.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1] / "events-preview"
CAP_PER_CITY = 24
SOURCES = {
    "ashdod": {"ashdod.smarticket.co.il", "mishkan-ashdod.smarticket.co.il"},
    "rishon-lezion": {"yama.smarticket.co.il"},
}
MONTHS = {
    "ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4,
    "מאי": 5, "יוני": 6, "יולי": 7, "אוגוסט": 8,
    "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12,
}
CIVIL_DATE = re.compile(r"\b(\d{1,2})\s+ב?(ינואר|פברואר|מרץ|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר)\s+(\d{4})\b")
# Avoid \\b after the shekel sign, which is not an alphanumeric character.
COST = re.compile(r"(?:^|\s)מחיר\s*:?\s*([0-9][0-9,]*)\s*(?:₪|ש\"ח|ש״ח)")
CLOCK = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\s*[-–]\s*([01]?\d|2[0-3]):([0-5]\d)\b")
MINUTES = re.compile(r"(?:משך\s*:?\s*)(?:(\d+)\s*שעות?|\bשעה\b)?\s*(?:ו[-\s]*)?(\d+)\s*דקות")
SIMPLE_DURATION = re.compile(r"משך\s*:\s*(\d+)\s*דקות")
UA = "ISNET-Events/1.0 (+public ticket pages, editorial listings)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "he-IL,he;q=0.9"})


def normalize(value):
    return re.sub(r"[\s\W_]+", " ", str(value or "").strip().casefold(), flags=re.UNICODE).strip()


def source_detail_url(event, city):
    url = event.get("ticket_url") or ""
    if not url.startswith("https://"):
        return None
    u = urlsplit(url)
    if u.hostname not in SOURCES[city] or "id" not in parse_qs(u.query):
        return None
    if not any(x.get("name", "").endswith("smarticket") or x.get("name") == "yama"
               for x in event.get("sources", [])):
        return None
    return url


def pull_html(url):
    try:
        r = SESSION.get(url, timeout=13, allow_redirects=True)
        if r.status_code in (401, 403, 429):
            return None, "blocked"
        if r.status_code != 200 or not r.url.startswith("https://"):
            return None, "http"
        if "html" not in r.headers.get("content-type", "").lower() or len(r.content) > 1_500_000:
            return None, "content"
        if urlsplit(r.url).hostname not in SOURCES["ashdod"] | SOURCES["rishon-lezion"]:
            return None, "redirected"
        return BeautifulSoup(r.content, "html.parser"), None
    except requests.RequestException:
        return None, "unavailable"


def detail_facts(soup, original):
    """Return only facts confirmed by a matching event heading + civil date."""
    h1 = soup.find("h1")
    if not h1:
        return {}
    heading = h1.get_text(" ", strip=True)
    if normalize(heading) != normalize(original.get("title")):
        return {}
    lines = [re.sub(r"\s+", " ", x).strip() for x in soup.stripped_strings]
    idx = next((i for i, x in enumerate(lines) if normalize(x) == normalize(heading)), -1)
    if idx < 0:
        return {}
    block = lines[idx+1:idx+20]
    # The Smarticket event page displays the official venue directly under H1.
    venue = ""
    for text in block[:6]:
        if text.startswith(("ביום ", "משך:", "מחיר", "הכרטיסים", "מפת הגעה", "תאריך")):
            break
        if "מפת הגעה" in text:
            text = text.split("מפת הגעה", 1)[0].strip(" ()")
        if 5 <= len(text) <= 150 and ("אשדוד" in text or "ראשון לציון" in text or "היכל" in text or "מרכז" in text):
            venue = text
            break
    full = " ".join(block[:17])
    dates = []
    for d in CIVIL_DATE.finditer(full):
        try:
            dates.append(date(int(d.group(3)), MONTHS[d.group(2)], int(d.group(1))).isoformat())
        except ValueError:
            continue
    if original.get("start_date") not in dates:
        return {}
    details = {}
    if venue:
        details["venue"] = venue
        if re.search(r"רח(?:וב|[׳'״])\s*[^,.]{2,75}\b\d{1,4}\b", venue):
            details["address"] = venue
    price = COST.search(full)
    if price:
        value = int(price.group(1).replace(",", ""))
        if 0 <= value <= 15000:
            details["price_min_ils"] = value
            details["price_max_ils"] = value
    if "הכרטיסים אזלו" in full or "אזלו הכרטיסים" in full:
        details["ticket_status"] = "sold_out"
    raw_minutes = SIMPLE_DURATION.search(full)
    if raw_minutes:
        details["duration_minutes"] = int(raw_minutes.group(1))
    else:
        # Example: "משך: שעה ו-30 דקות" + confirmed 18:00 - 19:30
        t = CLOCK.search(full)
        if t:
            start = int(t.group(1))*60+int(t.group(2))
            end = int(t.group(3))*60+int(t.group(4))
            if 0 < (end-start) <= 10*60:
                details["duration_minutes"] = end-start
    if urlsplit(original.get("ticket_url", "")).hostname == "ashdod.smarticket.co.il":
        details["ticket_provider"] = "החברה העירונית לתרבות ופנאי באשדוד"
    return details


def run():
    total=0
    today=date.today()
    for city, hosts in SOURCES.items():
        path=ROOT/city/"data/events.json"
        doc=json.loads(path.read_text(encoding="utf-8"))
        events=doc["events"]
        candidates=sorted(
            [e for e in events if source_detail_url(e, city)
             and today-timedelta(days=1) <= date.fromisoformat(e["start_date"]) <= today+timedelta(days=75)
             and (not e.get("detail_checked_at") or e["detail_checked_at"] < (today-timedelta(days=7)).isoformat())
             and (not e.get("address") or e.get("price_min_ils") is None or not e.get("ticket_provider"))],
            key=lambda e: (e["start_date"],e.get("start_time") or "99:99"),
        )
        checked=updated=0
        blocked=set()
        for e in candidates:
            if checked >= CAP_PER_CITY:
                break
            url=source_detail_url(e,city)
            host=urlsplit(url).hostname
            if host in blocked:
                continue
            checked+=1
            soup, error=pull_html(url)
            e["detail_checked_at"]=today.isoformat()
            if error:
                if error == "blocked":
                    blocked.add(host)
                continue
            facts=detail_facts(soup,e)
            if not facts:
                continue
            changes=0
            for field, value in facts.items():
                # Detailed source fields are authoritative, but do not rewrite
                # editorial titles, descriptions, organizer contact info.
                if e.get(field)!=value:
                    e[field]=value
                    changes+=1
            if changes:
                updated+=1
            e["detail_source_url"]=url
            e["details_verified"]=True
        if checked:
            doc["detail_enrichment_checked_at"]=datetime.now(timezone.utc).isoformat()
            path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        total+=updated
        print(f"{city}: {checked} official detail pages checked, {updated} records enriched, blocked_hosts={sorted(blocked)}",flush=True)
    print(f"Total enriched records: {total}",flush=True)


if __name__ == "__main__":
    run()

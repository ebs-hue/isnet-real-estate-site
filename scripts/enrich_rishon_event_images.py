#!/usr/bin/env python3
"""Replace Rishon LeZion event placeholders with checked, local official images.

Only a real event/show detail page matching the event title may supply a photo.
Never label a venue graphic or a generic site logo as an event photograph.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import time
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "events-preview" / "rishon-lezion"
DATA = SITE / "data" / "events.json"
REPORT = SITE / "data" / "image-audit.json"
OUT = SITE / "assets" / "events"
AGENTS = {"User-Agent": "Mozilla/5.0 (compatible; ISNET-EventsImageQA/1.0; editorial event listings)", "Accept-Language": "he-IL,he;q=0.9,en;q=0.8"}
SITES = {
    "htrl": ["https://htrl.co.il/show/", "https://htrl.co.il/", "https://htrl.co.il/לוח-שנה/"],
    "kotar_rishon": ["https://www.kotar-rishon-lezion.org.il/events-category/eventsactivities/"],
    "yama": ["https://yama.smarticket.co.il/"],
    "RIZONE+": ["https://club.rishonlezion.muni.il/"],
    "Eventim": ["https://www.eventim.co.il/"],
}
GENERIC = ("logo", "favicon", "placeholder", "default", "no-image", "no_image", "sprite", "icon", "avatar", "blank", "loading", "pixel")
session = requests.Session()
session.headers.update(AGENTS)
cache = {}
link_indexes = {}

def norm(value):
    v = unicodedata.normalize("NFKC", str(value or "")).casefold()
    v = re.sub(r"[\u0591-\u05c7]", "", v)
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zא-ת]+", " ", v)).strip()

def title_score(title, candidate):
    a, b = norm(title), norm(candidate)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    sa, sb = set(a.split()), set(b.split())
    if (a in b or b in a) and min(len(a), len(b)) > 6:
        return .91
    return .65 * SequenceMatcher(None, a, b).ratio() + .35 * len(sa & sb) / max(len(sa), len(sb))

def fetch(url, binary=False):
    if not url.startswith("https://"):
        return None
    if not binary and url in cache:
        return cache[url]
    try:
        r = session.get(url, timeout=18, allow_redirects=True, stream=True)
        r.raise_for_status()
        ctype = r.headers.get("content-type", "").lower()
        cap = 9_000_000 if binary else 2_500_000
        buf = bytearray()
        for chunk in r.iter_content(65536):
            buf.extend(chunk)
            if len(buf) > cap:
                raise ValueError("response exceeds limit")
        if binary:
            if not ctype.startswith("image/"):
                return None
            return bytes(buf)
        if "html" not in ctype and "xml" not in ctype and "text" not in ctype:
            return None
        r.encoding = r.apparent_encoding or "utf-8"
        result = (r.url, BeautifulSoup(bytes(buf), "html.parser"))
        cache[url] = result
        return result
    except (requests.RequestException, ValueError):
        return None

def link_index(source):
    if source in link_indexes:
        return link_indexes[source]
    candidates = []
    for base in SITES.get(source, []):
        response = fetch(base)
        if not response:
            continue
        actual, doc = response
        for a in doc.find_all("a", href=True):
            url = urljoin(actual, a["href"])
            if urlparse(url).hostname != urlparse(actual).hostname:
                continue
            label = a.get_text(" ", strip=True)
            label += " " + (a.find(["h2", "h3", "h4"]).get_text(" ", strip=True) if a.find(["h2", "h3", "h4"]) else "")
            if label:
                candidates.append((label, url))
    if source == "htrl":
        candidates.extend(htrl_sitemaps())
    link_indexes[source] = candidates
    return candidates

def htrl_sitemaps():
    sitemap_paths = [
        "https://htrl.co.il/show-sitemap.xml",
        "https://htrl.co.il/wp-sitemap-posts-show-1.xml",
        "https://htrl.co.il/sitemap_index.xml",
        "https://htrl.co.il/wp-sitemap.xml",
    ]
    out, visited, pending = [], set(), list(sitemap_paths)
    while pending and len(visited) < 24:
        u = pending.pop(0)
        if u in visited:
            continue
        visited.add(u)
        parsed = fetch(u)
        if not parsed:
            continue
        _, doc = parsed
        for loc in doc.find_all("loc"):
            url = loc.get_text(" ", strip=True)
            if not url.startswith("https://htrl.co.il/"):
                continue
            if url.lower().endswith(".xml") and ("show" in url or "post" in url or "sitemap" in url):
                if url not in visited and url not in pending:
                    pending.append(url)
            elif "/show/" in url:
                tail = unquote(urlparse(url).path.rstrip("/").split("/")[-1]).replace("-", " ")
                out.append((tail, url))
    return out

def possible_details(e):
    source = (e.get("sources") or [{}])[0].get("name", "")
    wanted = e.get("title", "")
    root = link_index(source)
    found = [(title_score(wanted, text), url) for text, url in root]
    if source == "htrl":
        for label, url in root:
            slug = unquote(urlparse(url).path.rstrip("/").split("/")[-1]).replace("-", " ")
            found.append((title_score(wanted, slug), url))
        slug = re.sub(r"\s+", "-", norm(wanted))
        found.append((.75, "https://htrl.co.il/show/" + quote(slug) + "/"))
    for u in [e.get("ticket_url"), e.get("purchase_url")]:
        if not u or not u.startswith("https://"):
            continue
        # Treat only event-specific links as detail pages, never category/home pages.
        path = urlparse(u).path.strip("/")
        if source == "htrl" and path.startswith("show/"):
            found.append((1.0, u))
        elif source in ("kotar_rishon", "yama", "RIZONE+", "Eventim") and len(path) > 35:
            found.append((.82, u))
    found.sort(reverse=True)
    seen, chosen = set(), []
    for score, u in found:
        if u not in seen and score >= .68:
            seen.add(u)
            chosen.append((score, u))
        if len(chosen) >= 7:
            break
    return chosen

def detail_matches(title, doc):
    h = doc.find("h1")
    if not h:
        return False
    return title_score(title, h.get_text(" ", strip=True)) >= .78

def image_candidates(doc, page_url, title):
    out = []
    for prop in ('og:image', 'og:image:url', 'twitter:image'):
        for m in doc.select('meta[property="' + prop + '"],meta[name="' + prop + '"]'):
            if m.get("content"):
                out.append((110, urljoin(page_url, m["content"])))
    main = doc.find("main") or doc.find("article") or doc.body
    if main:
        for img in main.select("img"):
            label = (img.get("alt") or "") + " " + (img.get("title") or "")
            score = 50 + round(35 * title_score(title, label))
            for attr in ("data-src", "data-lazy-src", "src"):
                if img.get(attr):
                    out.append((score, urljoin(page_url, img[attr])))
            if img.get("srcset"):
                out.append((score, urljoin(page_url, img["srcset"].split(",")[-1].strip().split()[0])))
    return sorted({u: (score, u) for score, u in out}.values(), reverse=True)

def download_photo(url, origin):
    if not url.startswith("https://"):
        return None
    if any(word in urlparse(url).path.lower().split("/")[-1] for word in GENERIC):
        return None
    try:
        session.headers["Referer"] = origin
        raw = fetch(url, binary=True)
        if not raw:
            return None
        with Image.open(io.BytesIO(raw)) as img:
            if img.width < 340 or img.height < 220 or img.width / img.height > 5 or img.height / img.width > 5:
                return None
            normalized = ImageOps.exif_transpose(img).convert("RGB")
            normalized.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
            dest = io.BytesIO()
            normalized.save(dest, "WEBP", quality=83, method=5)
            return dest.getvalue()
    except (OSError, ValueError, requests.RequestException):
        return None
    finally:
        session.headers.pop("Referer", None)

def enrich():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    events = doc.get("events", [])
    OUT.mkdir(parents=True, exist_ok=True)
    found = {}
    photo_owners = {}
    used = {}
    failures = []
    reasons = Counter()
    for ix, e in enumerate(events, 1):
        title = e.get("title", "")
        current = e.get("image_url") or ""
        if e.get("image_strategy") == "official_event_poster" and current.startswith("assets/events/") and (SITE / current).is_file():
            found[e.get("event_id")] = current
            continue
        # Legacy SVG placeholders were incorrectly flagged as 'verified'.
        e["image_verified"] = False
        e["image_publishable"] = False
        e["thumbnail_ready"] = False
        e["thumbnail_url"] = None
        e["image_strategy"] = "awaiting_official_event_image"
        source = (e.get("sources") or [{}])[0].get("name", "")
        key = (source, norm(title))
        if key in used:
            previous = used[key]
            if previous:
                e.update(previous)
                found[e.get("event_id")] = previous["image_url"]
                reasons["same_production_reused"] += 1
            continue
        matched = None
        details = possible_details(e)
        for _, page in details:
            p = fetch(page)
            if not p:
                continue
            actual, html = p
            if not detail_matches(title, html):
                continue
            for _, image_url in image_candidates(html, actual, title)[:12]:
                raw = download_photo(image_url, actual)
                if not raw:
                    continue
                checksum = hashlib.sha256(raw).hexdigest()
                previous_title = photo_owners.get(checksum)
                if previous_title and title_score(previous_title, title) < .75:
                    continue
                photo_owners[checksum] = title
                name = checksum[:24] + ".webp"
                (OUT / name).write_bytes(raw)
                rel = "assets/events/" + name
                matched = {
                    "image_url": rel,
                    "image_source": actual,
                    "image_origin_url": image_url,
                    "image_credit": "צילום או כרזה: אתר המארגן הרשמי",
                    "image_publishable": True,
                    "image_verified": True,
                    "image_strategy": "official_event_poster",
                    "thumbnail_url": rel,
                    "thumbnail_ready": True,
                }
                break
            if matched:
                break
        used[key] = matched
        if matched:
            e.update(matched)
            found[e.get("event_id")] = matched["image_url"]
            reasons[source + "_matched"] += 1
            print(f"{ix:02}/{len(events)} VERIFIED: {title}", flush=True)
        else:
            failures.append({"event_id": e.get("event_id"), "title": title, "source": source, "candidate_pages": [u for _, u in details[:3]]})
            reasons[source + "_missing"] += 1
            print(f"{ix:02}/{len(events)} REVIEW: {title}", flush=True)
        time.sleep(.1)
    doc["image_audit_generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "generated_at": doc["image_audit_generated_at"],
        "total_events": len(events),
        "verified_event_photos": sum(1 for e in events if e.get("image_verified") is True and e.get("image_strategy") == "official_event_poster"),
        "unverified_event_photos": sum(1 for e in events if e.get("image_verified") is not True),
        "breakdown": dict(reasons),
        "manual_review": failures,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("IMAGE AUDIT", json.dumps({k: v for k, v in report.items() if k != "manual_review"}, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    enrich()

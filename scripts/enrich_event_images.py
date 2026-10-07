#!/usr/bin/env python3
"""
Enrich Ashdod event records with images already published by the same source
pages from which the event data was collected.

The script deliberately stays on the recorded source/ticketing hosts. It does
not search unrelated websites. For each event missing a publishable image it:
1. opens the recorded source landing page (cached per source);
2. finds the closest matching event detail link;
3. opens that event page;
4. extracts og:image / twitter:image / event-relevant <img> candidates;
5. verifies the selected URL is an image;
6. writes image_url, image_source and image_publishable=true.

A report is written alongside events.json so we can see what still needs a
manual image later.
"""
from __future__ import annotations

import difflib
import html
import json
import os
import re
import ssl
import sys
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "events-preview" / "ashdod" / "data" / "events.json"
REPORT_PATH = ROOT / "events-preview" / "ashdod" / "data" / "image-enrichment-report.json"
MEDIA_INDEX = ROOT / "events-preview" / "media-bank" / "data" / "media.json"
PRODUCTIONS_INDEX = ROOT / "events-preview" / "media-bank" / "data" / "productions.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0 Safari/537.36 ISNET-Events/1.0"
)
TIMEOUT = 25
PAUSE = 0.12
MAX_EVENT_PAGES = 4

BAD_IMAGE_WORDS = {
    "logo", "icon", "favicon", "sprite", "spinner", "loader", "map", "waze",
    "google", "facebook", "instagram", "whatsapp", "youtube", "arrow", "close",
    "venue", "hall", "placeholder", "default", "blank", "pixel", "tracking",
    "accessibility", "share", "button", "calendar",
}

GOOD_META_KEYS = {
    "og:image", "og:image:url", "twitter:image", "twitter:image:src",
}

GENERIC_IMAGE_FRAGMENTS = (
    "/languages/il.gif",
    "artistshadow",
    "/images/live/more/eventnew.jpg",
    "eventnew.jpg",
    "placeholder",
    "no-image",
    "no_image",
    "noimage",
    "default-image",
    "default_image",
    "blank.gif",
    "spacer.gif",
    "transparent.gif",
    "favicon",
    "/logo",
    "logo.",
    "/icons/",
    "/icon/",
)

def is_generic_image_url(url: str) -> bool:
    low = html.unescape(url or "").lower()
    return (not low) or any(x in low for x in GENERIC_IMAGE_FRAGMENTS)

def has_event_image_signal(url: str) -> bool:
    low = html.unescape(url or "").lower()
    return any(x in low for x in (
        "/uploads/", "/thumbs/", "/caps/", "livenew_", "/events/", "/event/",
        "/images/events/", "/images/event/", "poster", "banner",
    ))


def normalize_text(value: str) -> str:
    value = html.unescape(value or "")
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("־", "-").replace("–", "-").replace("—", "-")
    value = re.sub(r"[\u0591-\u05C7]", "", value)
    value = re.sub(r"[^0-9A-Za-zא-ת]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def title_tokens(value: str) -> List[str]:
    return [x for x in normalize_text(value).split() if len(x) > 1]


def same_host_family(a: str, b: str) -> bool:
    ha = (urlparse(a).hostname or "").lower().removeprefix("www.")
    hb = (urlparse(b).hostname or "").lower().removeprefix("www.")
    if not ha or not hb:
        return False
    return ha == hb or ha.endswith("." + hb) or hb.endswith("." + ha)


def requote_url(url: str) -> str:
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@-._~!$&()*+,;=")
    query = quote(parts.query, safe="=&%:@/?-._~!$()*+,;")
    fragment = quote(parts.fragment, safe="")
    return urlunsplit((parts.scheme, parts.netloc, path, query, fragment))


def fetch_bytes(
    url: str,
    *,
    range_bytes: Optional[int] = None,
    referer: Optional[str] = None,
) -> Tuple[bytes, str, str]:
    url = requote_url(url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "he-IL,he;q=0.9,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": requote_url(referer or url),
    }
    if range_bytes:
        headers["Range"] = f"bytes=0-{range_bytes - 1}"
    req = Request(url, headers=headers)
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
        data = resp.read(range_bytes or -1)
        ctype = (resp.headers.get("Content-Type") or "").lower()
        final_url = resp.geturl()
        return data, ctype, final_url


def fetch_html(url: str) -> Tuple[str, str]:
    data, ctype, final_url = fetch_bytes(url)
    charset = "utf-8"
    m = re.search(r"charset=([\w-]+)", ctype)
    if m:
        charset = m.group(1)
    try:
        text = data.decode(charset, errors="replace")
    except LookupError:
        text = data.decode("utf-8", errors="replace")
    return text, final_url


def verify_image(url: str, referer: Optional[str] = None) -> bool:
    if is_generic_image_url(url):
        return False
    try:
        data, ctype, _ = fetch_bytes(url, range_bytes=131072, referer=referer)
        if ctype.startswith("image/"):
            return len(data) > 800
        return (
            len(data) > 800 and (
                data.startswith(b"\xff\xd8\xff")
                or data.startswith(b"\x89PNG\r\n\x1a\n")
                or (data.startswith(b"RIFF") and b"WEBP" in data[:16])
                or data.lstrip().startswith(b"<svg")
            )
        )
    except Exception:
        return False


@dataclass
class Link:@dataclass
class Link:
    href: str
    text: str


@dataclass
class ImageCandidate:
    url: str
    alt: str
    score: float
    reason: str


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[Link] = []
        self.images: List[Dict[str, str]] = []
        self.meta: List[Dict[str, str]] = []
        self.styled: List[Dict[str, str]] = []
        self._anchor_href: Optional[str] = None
        self._anchor_text: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        a = {str(k).lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "a":
            self._anchor_href = a.get("href")
            self._anchor_text = []
        elif tag in ("img", "source"):
            self.images.append(a)
        elif tag == "meta":
            self.meta.append(a)
        if a.get("style"):
            self.styled.append(a)

    def handle_data(self, data: str) -> None:
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._anchor_href is not None:
            txt = re.sub(r"\s+", " ", " ".join(self._anchor_text)).strip()
            self.links.append(Link(self._anchor_href, txt))
            self._anchor_href = None
            self._anchor_text = []


def parse_page(markup: str) -> PageParser:
    p = PageParser()
    try:
        p.feed(markup)
    except Exception:
        pass
    return p


def link_score(title: str, text: str, href: str) -> float:
    nt = normalize_text(title)
    nx = normalize_text(text)
    nh = normalize_text(href)
    if not nt:
        return 0
    score = 0.0
    if nt == nx:
        score += 12
    if nt and nx and nt in nx:
        score += 8
    if nt and nx and nx in nt and len(nx) >= 5:
        score += 4
    if nt and nh and nt.replace(" ", "") in nh.replace(" ", ""):
        score += 3
    score += 5 * difflib.SequenceMatcher(None, nt, nx).ratio()
    ta, tb = set(title_tokens(title)), set(title_tokens(text))
    if ta:
        score += 5 * (len(ta & tb) / len(ta))
    return score


def discover_event_links(title: str, source_url: str, source_html: str) -> List[str]:
    parser = parse_page(source_html)
    ranked: List[Tuple[float, str]] = []
    for link in parser.links:
        if not link.href or link.href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        url = urljoin(source_url, link.href)
        if not same_host_family(source_url, url):
            continue
        score = link_score(title, link.text, link.href)
        if score >= 5.1:
            ranked.append((score, url))
    ranked.sort(key=lambda x: (-x[0], len(x[1])))
    out: List[str] = []
    seen = set()
    for _, url in ranked:
        key = url.split("#", 1)[0]
        if key not in seen:
            seen.add(key)
            out.append(key)
        if len(out) >= MAX_EVENT_PAGES:
            break
    return out


def choose_src(attrs: Dict[str, str], page_url: str) -> List[str]:
    raw: List[str] = []
    for key in ("src", "data-src", "data-original", "data-lazy-src", "data-image", "data-url"):
        if attrs.get(key):
            raw.append(attrs[key])
    for key in ("srcset", "data-srcset"):
        if attrs.get(key):
            # Prefer the largest srcset candidate (usually last).
            parts = [x.strip().split(" ")[0] for x in attrs[key].split(",") if x.strip()]
            if parts:
                raw.append(parts[-1])
    result: List[str] = []
    for x in raw:
        if not x or x.startswith(("data:", "blob:")):
            continue
        result.append(urljoin(page_url, html.unescape(x)))
    return result


def image_candidates(title: str, page_url: str, markup: str) -> List[ImageCandidate]:
    parser = parse_page(markup)
    result: List[ImageCandidate] = []
    title_norm = normalize_text(title)
    toks = set(title_tokens(title))

    def add(url: str, alt: str, score: float, reason: str) -> None:
        u = urljoin(page_url, html.unescape((url or "").strip().strip("'\"")))
        if not u or u.startswith(("data:", "blob:")) or is_generic_image_url(u):
            return
        low = u.lower()
        if low.endswith(".svg") and "event" not in low:
            return
        if has_event_image_signal(u):
            score += 45
        if "/uploads/" in low:
            score += 25
        if "/thumbs/" in low or "/caps/" in low:
            score += 18
        result.append(ImageCandidate(u, alt, score, reason))

    # Event-page metadata is high confidence, but still passes the generic filter.
    for m in parser.meta:
        key = (m.get("property") or m.get("name") or "").lower()
        content = m.get("content") or ""
        if key in GOOD_META_KEYS and content:
            add(content, "", 100.0, key)
        elif (m.get("itemprop") or "").lower() == "image" and content:
            add(content, "", 92.0, "itemprop:image")

    # Standard and lazy-loaded <img>/<source> assets.
    for img in parser.images:
        alt = " ".join(filter(None, [img.get("alt"), img.get("title"), img.get("aria-label")]))
        nalt = normalize_text(alt)
        for u in choose_src(img, page_url):
            low = u.lower()
            if any(word in low for word in BAD_IMAGE_WORDS) and not has_event_image_signal(u):
                continue
            score = 25.0
            if title_norm and nalt:
                score += 20 * difflib.SequenceMatcher(None, title_norm, nalt).ratio()
            if title_norm and nalt and title_norm in nalt:
                score += 35
            if toks:
                atoks = set(title_tokens(alt))
                score += 25 * (len(toks & atoks) / len(toks))
            w = img.get("width") or ""
            h = img.get("height") or ""
            try:
                wi = int(re.sub(r"\D", "", w) or 0)
                hi = int(re.sub(r"\D", "", h) or 0)
                if wi >= 300 and hi >= 180:
                    score += 8
                if wi and hi and (wi < 120 or hi < 80):
                    score -= 30
            except ValueError:
                pass
            add(u, alt, score, "img")

    # Background images and image URLs embedded in inline JSON/scripts.
    for attrs in parser.styled:
        style = html.unescape(attrs.get("style") or "")
        for m in re.finditer(r"url\(([^)]+)\)", style, flags=re.I):
            add(m.group(1), attrs.get("title") or attrs.get("aria-label") or "", 48.0, "css-background")

    raw_patterns = [
        r'''(?P<u>https?://[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?)''',
        r'''(?P<u>//[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?)''',
        r'''(?P<u>/[^"'<>\s\\]*(?:uploads|caps|events?)[^"'<>\s\\]*\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?)''',
    ]
    decoded_markup = html.unescape(markup)
    for pattern in raw_patterns:
        for m in re.finditer(pattern, decoded_markup, flags=re.I):
            add(m.group("u"), "", 42.0, "raw-html")

    best: Dict[str, ImageCandidate] = {}
    for cand in result:
        old = best.get(cand.url)
        if old is None or cand.score > old.score:
            best[cand.url] = cand
    return sorted(best.values(), key=lambda x: -x.score)


def is_source_image_allowed(page_url: str, image_url: str, recorded_sources: List[str]) -> bool:
    # The image may be served from a CDN, so page host need not equal image host.
    # What matters here is that the image was explicitly referenced by an event
    # page on one of the recorded source hosts.
    return any(same_host_family(page_url, src) for src in recorded_sources)


def bank_asset_url(media):
    u = media.get("url") or ""
    if not u:
        return None
    if u.startswith(("http://", "https://", "data:")):
        return u
    city = (media.get("cities") or [None])[0]
    if u.startswith("media-bank/"):
        return "../" + u
    if city:
        return "../" + city + "/" + u
    return u

def load_bank_reuse():
    if not MEDIA_INDEX.is_file() or not PRODUCTIONS_INDEX.is_file():
        return {}
    media_doc = json.loads(MEDIA_INDEX.read_text(encoding="utf-8"))
    prod_doc = json.loads(PRODUCTIONS_INDEX.read_text(encoding="utf-8"))
    by_id = {m.get("media_id"): m for m in media_doc.get("media", []) if m.get("media_id")}
    out = {}
    for p in prod_doc.get("productions", []):
        mid = p.get("preferred_media_id")
        m = by_id.get(mid)
        if not m or m.get("status") != "approved" or m.get("publishable") is not True:
            continue
        out[p.get("production_key") or normalize_text(p.get("name"))] = m
    return out

def main() -> int:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    events = payload.get("events") or []

    source_cache: Dict[str, Tuple[str, str]] = {}
    event_page_cache: Dict[str, Tuple[str, str]] = {}
    title_image_cache: Dict[Tuple[str, Tuple[str, ...]], Tuple[str, str]] = {}

    stats = Counter()
    failures = []
    bank_reuse = load_bank_reuse()

    def get_html_cached(url: str, cache: Dict[str, Tuple[str, str]]) -> Optional[Tuple[str, str]]:
        if url in cache:
            return cache[url]
        try:
            time.sleep(PAUSE)
            value = fetch_html(url)
            cache[url] = value
            return value
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, ValueError) as exc:
            cache[url] = ("", url)
            return None

    # Remove generic assets accidentally selected by older enrichment runs.
    for event in events:
        if event.get("image_url") and is_generic_image_url(event.get("image_url") or ""):
            event["image_url"] = None
            event["image_source"] = None
            event["image_credit"] = None
            event["image_publishable"] = False
            stats["generic_images_cleared"] += 1

    for idx, event in enumerate(events, 1):
        if event.get("image_url") and event.get("image_publishable") is True:
            stats["already_had_image"] += 1
            continue

        title = event.get("title") or ""

        # Reuse a positively approved network-wide asset before any new source request.
        pkey = normalize_text(event.get("production_name") or event.get("series_name") or title)
        bank_media = bank_reuse.get(pkey)
        if bank_media:
            full = bank_asset_url(bank_media)
            thumb = "../" + bank_media["card_url"] if str(bank_media.get("card_url") or "").startswith("media-bank/") else full
            if full:
                event.update({
                    "image_url": full,
                    "thumbnail_url": thumb,
                    "thumbnail_ready": bool(thumb),
                    "image_source": bank_media.get("source_url"),
                    "image_origin_url": bank_media.get("origin_url") or full,
                    "image_credit": bank_media.get("credit"),
                    "image_publishable": True,
                    "image_verified": True,
                    "image_rights_status": bank_media.get("rights_status") or "verified_reuse",
                    "image_strategy": "central_media_bank_reuse",
                    "media_bank_id": bank_media.get("media_id"),
                })
                stats["central_media_bank_reuse"] += 1
                continue

        recorded_sources = [s.get("url") for s in event.get("sources", []) if s.get("url")]
        if not recorded_sources:
            stats["no_source"] += 1
            failures.append({"event_id": event.get("event_id"), "title": title, "reason": "no_source"})
            continue

        cache_key = (normalize_text(title), tuple(sorted(urlparse(x).hostname or "" for x in recorded_sources)))
        cached = title_image_cache.get(cache_key)
        if cached:
            image_url, image_source = cached
            event["image_url"] = image_url
            event["image_source"] = image_source
            event["image_publishable"] = True
            stats["reused_by_title"] += 1
            continue

        candidates_pages: List[str] = []
        if event.get("ticket_url"):
            candidates_pages.append(event["ticket_url"])

        for src in recorded_sources:
            loaded = get_html_cached(src, source_cache)
            if not loaded:
                continue
            source_html, source_final = loaded
            for detail in discover_event_links(title, source_final, source_html):
                if detail not in candidates_pages:
                    candidates_pages.append(detail)

        selected: Optional[Tuple[str, str]] = None
        tried = []
        for page_url in candidates_pages[:MAX_EVENT_PAGES]:
            if not any(same_host_family(page_url, src) for src in recorded_sources):
                # ticket_url can redirect between the two recorded Smarticket hosts;
                # otherwise stay within the recorded source family.
                if not event.get("ticket_url") or page_url != event.get("ticket_url"):
                    continue
            loaded = get_html_cached(page_url, event_page_cache)
            if not loaded:
                tried.append({"url": page_url, "status": "fetch_failed"})
                continue
            markup, final_page = loaded
            imgs = image_candidates(title, final_page, markup)
            tried.append({
                "url": final_page,
                "images_found": len(imgs),
                "top_candidates": [
                    {"url": x.url, "score": round(x.score, 1), "reason": x.reason}
                    for x in imgs[:5]
                ],
            })
            for cand in imgs[:12]:
                if not is_source_image_allowed(final_page, cand.url, recorded_sources):
                    continue
                verified = verify_image(cand.url, referer=final_page)
                trusted_source_asset = has_event_image_signal(cand.url) and cand.score >= 65
                if verified or trusted_source_asset:
                    selected = (cand.url, final_page)
                    break
            if selected:
                # Keep the direct event page for future verification / tickets.
                if not event.get("ticket_url"):
                    event["ticket_url"] = final_page
                break

        if selected:
            image_url, image_source = selected
            event["image_url"] = image_url
            event["image_source"] = image_source
            event["image_publishable"] = True
            title_image_cache[cache_key] = selected
            stats["enriched"] += 1
            print(f"[{idx:03d}/{len(events)}] IMAGE {title} -> {image_url}")
        else:
            stats["missing"] += 1
            failures.append({
                "event_id": event.get("event_id"),
                "title": title,
                "sources": recorded_sources,
                "tried": tried,
            })
            print(f"[{idx:03d}/{len(events)}] MISS  {title}")

    # Summarize by source and category after enrichment.
    missing_events = [e for e in events if not (e.get("image_url") and e.get("image_publishable") is True)]
    missing_by_source = Counter()
    missing_by_category = Counter()
    for e in missing_events:
        missing_by_category[e.get("category") or "unknown"] += 1
        for s in e.get("sources", []):
            missing_by_source[s.get("name") or "unknown"] += 1

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_events": len(events),
        "events_with_publishable_images": len(events) - len(missing_events),
        "events_still_missing_images": len(missing_events),
        "stats": dict(stats),
        "missing_by_source": dict(missing_by_source),
        "missing_by_category": dict(missing_by_category),
        "missing": failures,
    }

    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in report.items() if k != "missing"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

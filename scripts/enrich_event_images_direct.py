#!/usr/bin/env python3
from __future__ import annotations

import difflib
import hashlib
import html
import json
import re
import ssl
import time
import unicodedata
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "events-preview" / "ashdod" / "data" / "events.json"
REPORT = ROOT / "events-preview" / "ashdod" / "data" / "image-enrichment-report.json"
OUT = ROOT / "events-preview" / "ashdod" / "assets" / "events"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
BAD_FRAGMENTS = (
    "artistshadow", "eventnew.jpg", "no_pic", "no-pic", "placeholder",
    "smarticket_logo", "_logo_", "/languages/", "favicon", "sprite", "spinner",
    "default-image", "default_image", "blank.gif", "spacer.gif"
)
ALLOWED_IMAGE_HOSTS = {
    "static.tickchak.co.il",
    "ashdod.smarticket.co.il",
    "mishkan-ashdod.smarticket.co.il",
    "static.smarticket.co.il",
}
PAGE_HOSTS = {
    "live.tickchak.co.il",
    "tickchak.co.il",
    "gveret-rabia.tickchak.co.il",
    "ashdod.smarticket.co.il",
    "mishkan-ashdod.smarticket.co.il",
}
TIMEOUT = 25
PAUSE = .12


def norm(s: str) -> str:
    s = html.unescape(s or "")
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("־", "-").replace("–", "-").replace("—", "-")
    s = re.sub(r"[\u0591-\u05C7]", "", s)
    s = re.sub(r"[^0-9A-Za-zא-ת]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def title_tokens(s: str) -> set[str]:
    stop = {"מופע", "באשדוד", "אשדוד", "של", "עם", "חדש", "הופעה", "הצגה", "סטנדאפ"}
    return {x for x in norm(s).split() if len(x) > 1 and x not in stop}


def title_match(event_title: str, page_title: str) -> float:
    a, b = norm(event_title), norm(page_title)
    if not a or not b:
        return 0.0
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = title_tokens(event_title), title_tokens(page_title)
    overlap = len(ta & tb) / max(1, len(ta))
    contains = 1.0 if a in b or b in a else 0.0
    return max(seq, overlap, contains)


def safe_url(url: str) -> str:
    p = urlsplit(url)
    return urlunsplit((
        p.scheme,
        p.netloc,
        quote(p.path, safe="/%:@-._~!$&()*+,;="),
        quote(p.query, safe="=&%:@/?-._~!$()*+,;"),
        "",
    ))


def host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def bad_image(url: str) -> bool:
    low = html.unescape(url or "").lower()
    return (not low) or any(x in low for x in BAD_FRAGMENTS)


def fetch(url: str, referer: str | None = None, limit: int | None = None):
    headers = {
        "User-Agent": UA,
        "Accept-Language": "he-IL,he;q=0.9,en;q=0.7",
        "Referer": safe_url(referer or url),
    }
    if limit:
        headers["Range"] = f"bytes=0-{limit-1}"
    req = Request(safe_url(url), headers=headers)
    with urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as r:
        return r.read(limit or -1), (r.headers.get("Content-Type") or "").lower(), r.geturl()


def fetch_html(url: str):
    raw, ctype, final = fetch(url)
    m = re.search(r"charset=([\w-]+)", ctype)
    enc = m.group(1) if m else "utf-8"
    try:
        text = raw.decode(enc, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    return text, final


class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = []
        self.title_parts = []
        self.in_title = False
        self.images = []

    def handle_starttag(self, tag, attrs):
        a = {str(k).lower(): (v or "") for k, v in attrs}
        t = tag.lower()
        if t == "meta":
            self.meta.append(a)
        elif t in ("img", "source"):
            self.images.append(a)
        elif t == "title":
            self.in_title = True

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False


def parse_page(markup: str) -> MetaParser:
    p = MetaParser()
    try:
        p.feed(markup)
    except Exception:
        pass
    return p


def page_identity(parser: MetaParser) -> str:
    for m in parser.meta:
        key = (m.get("property") or m.get("name") or "").lower()
        if key in ("og:title", "twitter:title") and m.get("content"):
            return html.unescape(m["content"])
    return re.sub(r"\s+", " ", " ".join(parser.title_parts)).strip()


def candidate_images(page_url: str, markup: str, parser: MetaParser):
    candidates = []

    def add(raw: str, score: int, why: str):
        u = urljoin(page_url, html.unescape((raw or "").strip().strip("'\"")))
        if not u or u.startswith(("data:", "blob:")) or bad_image(u):
            return
        if host(u) not in ALLOWED_IMAGE_HOSTS:
            return
        low = u.lower()
        if "/caps/" in low:
            score += 25
        if "livenew_" in low:
            score += 25
        if "/uploads/" in low:
            score += 20
        if "/thumbs/" in low:
            score += 12
        candidates.append((score, u, why))

    for m in parser.meta:
        key = (m.get("property") or m.get("name") or "").lower()
        val = m.get("content") or ""
        if key in ("og:image", "og:image:url", "twitter:image", "twitter:image:src") and val:
            add(val, 120, key)
        if (m.get("itemprop") or "").lower() == "image" and val:
            add(val, 105, "itemprop:image")

    for attrs in parser.images:
        for k in ("src", "data-src", "data-original", "data-lazy-src", "data-image"):
            if attrs.get(k):
                add(attrs[k], 50, "img")
        for k in ("srcset", "data-srcset"):
            if attrs.get(k):
                parts = [x.strip().split(" ")[0] for x in attrs[k].split(",") if x.strip()]
                if parts:
                    add(parts[-1], 55, "srcset")

    decoded = html.unescape(markup)
    for pat in (
        r'''https?://[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
        r'''//[^"'<>\s\\]+\.(?:jpe?g|png|webp|gif)(?:\?[^"'<>\s\\]*)?''',
    ):
        for m in re.finditer(pat, decoded, re.I):
            add(m.group(0), 35, "raw")

    best = {}
    for row in candidates:
        if row[1] not in best or row[0] > best[row[1]][0]:
            best[row[1]] = row
    return sorted(best.values(), reverse=True)


def verify_image(url: str, referer: str) -> bool:
    if bad_image(url):
        return False
    try:
        raw, ctype, _ = fetch(url, referer=referer, limit=160000)
        if ctype.startswith("image/"):
            return len(raw) > 1000
        return len(raw) > 1000 and (
            raw.startswith(b"\xff\xd8\xff")
            or raw.startswith(b"\x89PNG\r\n\x1a\n")
            or (raw.startswith(b"RIFF") and b"WEBP" in raw[:16])
            or raw.startswith((b"GIF87a", b"GIF89a"))
        )
    except Exception:
        return False


def cache_image(url: str, referer: str, seen: dict[str, str]) -> str | None:
    if url in seen:
        return seen[url]
    try:
        raw, ctype, _ = fetch(url, referer=referer)
        if len(raw) < 1000:
            return None
        path = urlsplit(url).path.lower()
        if path.endswith((".jpg", ".jpeg")):
            ext = ".jpg"
        elif path.endswith(".png"):
            ext = ".png"
        elif path.endswith(".webp"):
            ext = ".webp"
        elif path.endswith(".gif"):
            ext = ".gif"
        else:
            ext = {
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
            }.get(ctype.split(";", 1)[0], ".jpg")
        name = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20] + ext
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_bytes(raw)
        rel = "assets/events/" + name
        seen[url] = rel
        return rel
    except Exception:
        return None


def is_specific_event_page(url: str) -> bool:
    h = host(url)
    p = urlsplit(url)
    if h not in PAGE_HOSTS:
        return False
    if h in {"live.tickchak.co.il", "tickchak.co.il", "gveret-rabia.tickchak.co.il"}:
        return "/event/" in p.path or bool(re.fullmatch(r"/\d+", p.path.rstrip("/")))
    if h.endswith("smarticket.co.il"):
        return bool(re.search(r"(?:^|&)id=\d+", p.query)) or len(p.path.strip("/")) > 3
    return False


def clear_suspicious_tickchak_duplicates(events):
    groups = defaultdict(list)
    for e in events:
        origin = e.get("image_origin_url") or ""
        if host(origin) == "static.tickchak.co.il":
            groups[origin].append(e)

    cleared = 0
    for origin, group in groups.items():
        titles = {norm(e.get("title") or "") for e in group}
        if len(titles) <= 1:
            continue
        for e in group:
            e["image_url"] = None
            e["image_origin_url"] = None
            e["image_source"] = None
            e["image_credit"] = None
            e["image_publishable"] = False
            cleared += 1
    return cleared


def main():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    events = payload.get("events") or []
    stats = Counter()
    failures = []
    page_cache = {}
    image_cache = {}

    stats["suspicious_tickchak_duplicates_cleared"] = clear_suspicious_tickchak_duplicates(events)

    for idx, e in enumerate(events, 1):
        title = e.get("title") or ""
        page_urls = []

        ticket = e.get("ticket_url") or ""
        if ticket and is_specific_event_page(ticket):
            page_urls.append(ticket)

        # Prefer any previously recorded exact page as a secondary candidate.
        image_source = e.get("image_source") or ""
        if image_source and is_specific_event_page(image_source) and image_source not in page_urls:
            page_urls.append(image_source)

        selected = None
        attempts = []

        for page_url in page_urls:
            if page_url in page_cache:
                loaded = page_cache[page_url]
            else:
                try:
                    time.sleep(PAUSE)
                    loaded = fetch_html(page_url)
                except Exception as exc:
                    loaded = None
                page_cache[page_url] = loaded

            if not loaded:
                attempts.append({"page": page_url, "status": "fetch_failed"})
                continue

            markup, final_page = loaded
            parser = parse_page(markup)
            page_title = page_identity(parser)
            match = title_match(title, page_title)

            # Direct event URLs still need a meaningful title match. This prevents
            # generic listing/social images from being attached to the wrong event.
            min_match = 0.42 if "tickchak.co.il" in host(final_page) else 0.34
            if page_title and match < min_match:
                attempts.append({
                    "page": final_page,
                    "page_title": page_title,
                    "title_match": round(match, 3),
                    "status": "title_mismatch",
                })
                continue

            imgs = candidate_images(final_page, markup, parser)
            attempts.append({
                "page": final_page,
                "page_title": page_title,
                "title_match": round(match, 3),
                "top_images": [
                    {"url": u, "score": s, "reason": why}
                    for s, u, why in imgs[:4]
                ],
            })

            for score, image_url, why in imgs[:8]:
                if score < 60:
                    continue
                if verify_image(image_url, final_page):
                    selected = (image_url, final_page, page_title, match, why)
                    break
            if selected:
                break

        if selected:
            image_url, page_url, page_title, match, why = selected
            local = cache_image(image_url, page_url, image_cache)
            if local:
                e["image_origin_url"] = image_url
                e["image_url"] = local
                e["image_source"] = page_url
                e["image_publishable"] = True
                stats["enriched_or_revalidated"] += 1
                if "smarticket.co.il" in host(page_url):
                    stats["from_smarticket"] += 1
                elif "tickchak.co.il" in host(page_url):
                    stats["from_tickchak"] += 1
                print(f"[{idx:03d}/{len(events)}] IMAGE {title} -> {local}")
                continue

        if e.get("image_url") and e.get("image_publishable") is True:
            stats["kept_existing"] += 1
        else:
            stats["missing"] += 1
            failures.append({
                "event_id": e.get("event_id"),
                "title": title,
                "ticket_url": ticket or None,
                "sources": e.get("sources") or [],
                "attempts": attempts,
            })
            print(f"[{idx:03d}/{len(events)}] MISS {title}")

    missing = [e for e in events if not (e.get("image_url") and e.get("image_publishable") is True)]
    by_source = Counter()
    by_category = Counter()
    for e in missing:
        by_category[e.get("category") or "unknown"] += 1
        for s in e.get("sources") or []:
            by_source[s.get("name") or "unknown"] += 1

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_events": len(events),
        "events_with_publishable_images": len(events) - len(missing),
        "events_still_missing_images": len(missing),
        "stats": dict(stats),
        "missing_by_source": dict(by_source),
        "missing_by_category": dict(by_category),
        "missing": failures,
    }

    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "missing"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

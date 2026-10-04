#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import ssl
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
EVENT_ROOT = ROOT / "events-preview" / "ashdod"
DATA = EVENT_ROOT / "data" / "events.json"
OUT = EVENT_ROOT / "assets" / "event-thumbs"

WIDTH = 720
HEIGHT = 540
JPEG_QUALITY = 90
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"


def safe_url(url: str) -> str:
    p = urlsplit(url)
    return urlunsplit((
        p.scheme,
        p.netloc,
        quote(p.path, safe="/%:@-._~!$&()*+,;="),
        quote(p.query, safe="=&%:@/?-._~!$()*+,;"),
        "",
    ))


def load_source(event: dict) -> Image.Image:
    src = str(event.get("image_url") or "")
    if src.startswith("assets/"):
        path = EVENT_ROOT / src
        return Image.open(path).convert("RGB")

    if src.startswith(("http://", "https://")):
        ref = event.get("image_source") or src
        req = Request(
            safe_url(src),
            headers={
                "User-Agent": UA,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": safe_url(str(ref)),
            },
        )
        with urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
            raw = r.read(15 * 1024 * 1024)
        return Image.open(io.BytesIO(raw)).convert("RGB")

    raise ValueError("unsupported image source")


def cover(img: Image.Image, size=(WIDTH, HEIGHT)) -> Image.Image:
    return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def contain_size(img: Image.Image, max_w: int, max_h: int) -> tuple[int, int]:
    w, h = img.size
    scale = min(max_w / w, max_h / h)
    return max(1, round(w * scale)), max(1, round(h * scale))


def make_shadow(size: tuple[int, int]) -> Image.Image:
    w, h = size
    shadow = Image.new("RGBA", (w + 34, h + 34), (0, 0, 0, 0))
    core = Image.new("RGBA", (w, h), (0, 0, 0, 125))
    shadow.alpha_composite(core, (17, 17))
    return shadow.filter(ImageFilter.GaussianBlur(13))


def composite_poster(img: Image.Image, ratio: float) -> Image.Image:
    # Extend the original artwork to a consistent 4:3 thumbnail using a soft
    # blurred background. The actual poster remains fully visible in front.
    bg = cover(img)
    bg = bg.filter(ImageFilter.GaussianBlur(26))
    bg = ImageEnhance.Brightness(bg).enhance(0.52)
    bg = ImageEnhance.Color(bg).enhance(0.85)

    # Portraits need more breathing room than square art.
    if ratio < 0.90:
        max_w, max_h = round(WIDTH * 0.60), round(HEIGHT * 0.92)
    else:
        max_w, max_h = round(WIDTH * 0.78), round(HEIGHT * 0.92)

    fw, fh = contain_size(img, max_w, max_h)
    fg = img.resize((fw, fh), Image.Resampling.LANCZOS)

    canvas = bg.convert("RGBA")
    x = (WIDTH - fw) // 2
    y = (HEIGHT - fh) // 2

    shadow = make_shadow((fw, fh))
    canvas.alpha_composite(shadow, (x - 17, y - 11))
    canvas.alpha_composite(fg.convert("RGBA"), (x, y))
    return canvas.convert("RGB")


def make_thumbnail(img: Image.Image) -> tuple[Image.Image, str]:
    w, h = img.size
    if not w or not h:
        raise ValueError("invalid dimensions")
    ratio = w / h

    # Most event photography/posters on established boards is shown in a 4:3
    # card. Landscape imagery can safely fill it; portrait/square posters are
    # preserved in full on an extended background.
    if ratio >= 1.25:
        return cover(img), "landscape_cover"
    return composite_poster(img, ratio), "poster_composite"


def thumb_key(event: dict) -> str:
    basis = "|".join([
        str(event.get("image_origin_url") or ""),
        str(event.get("image_url") or ""),
        str(event.get("event_id") or ""),
        "thumb-v1-720x540",
    ])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:22]


def main() -> int:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    events = payload.get("events") or []
    OUT.mkdir(parents=True, exist_ok=True)

    generated = 0
    failed = 0
    skipped = 0

    for event in events:
        if not (
            event.get("image_verified") is True
            and event.get("image_publishable") is True
            and event.get("image_url")
        ):
            event["thumbnail_url"] = None
            event["thumbnail_ready"] = False
            skipped += 1
            continue

        try:
            img = load_source(event)
            thumb, strategy = make_thumbnail(img)
            name = thumb_key(event) + ".jpg"
            path = OUT / name
            thumb.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
            event["thumbnail_url"] = "assets/event-thumbs/" + name
            event["thumbnail_ready"] = True
            event["thumbnail_ratio"] = "4:3"
            event["thumbnail_strategy"] = strategy
            generated += 1
            print("THUMB", event.get("title"), event["thumbnail_url"], strategy)
        except Exception as exc:
            event["thumbnail_url"] = None
            event["thumbnail_ready"] = False
            event["thumbnail_error"] = type(exc).__name__
            failed += 1
            print("FAILED", event.get("title"), type(exc).__name__)

    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "generated": generated,
        "failed": failed,
        "skipped_without_verified_image": skipped,
        "total": len(events),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

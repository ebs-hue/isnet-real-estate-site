#!/usr/bin/env python3
"""Single-source ISNET events UI: Ashdod changes propagate to Rishon LeZion.

Ashdod's frontend is the canonical presentation template. Event data, cinema data,
sports data, local image assets, fallback configuration and places data remain
city-owned and are never copied. This only copies root-level HTML, CSS and JS.
"""
from __future__ import annotations

import argparse
import difflib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "events-preview"
MASTER = ROOT / "ashdod"
TARGETS = {
    "rishon-lezion": {
        "name": "ראשון לציון",
        "brand": "ראשון נט",
        "website": "https://www.rishonet.com/",
        "second_cinema": "פלאנט",
        "second_cinema_id": "planet",
    },
}
FRONTEND_EXTENSIONS = {".html", ".css", ".js"}
SKIP_NAMES = set()
HEAD_MARKER = "<!-- ISNET shared layout: edit the Ashdod source; synced automatically -->"
CSS_MARKER = "/* ISNET shared layout: edit events-preview/ashdod, not this generated file. */"
JS_MARKER = "// ISNET shared layout: edit events-preview/ashdod, not this generated file."


def localize(content: str, name: str, city: dict, suffix: str) -> str:
    # These are authored interface strings. Source data is NOT changed.
    content = content.replace("https://ashdodnet.com/", city["website"])
    content = content.replace("https://ashdodnet.com", city["website"].rstrip("/"))
    content = content.replace("אשדוד נט", city["brand"])
    content = content.replace("אשדוד", city["name"])
    # Cinema venues are city-specific. Preserve IDs on the canonical Ashdod site.
    content = content.replace("HOT Cinema", city["second_cinema"])
    content = content.replace('data-cinema="hot-cinema"', 'data-cinema="' + city["second_cinema_id"] + '"')
    content = content.replace('id==="hot-cinema"', 'id==="' + city["second_cinema_id"] + '"')
    # Avoid hardcoded dates on JS/CSS bundle URLs: the deployment adds fresh HTML
    # every time the Ashdod source changes.
    if suffix == ".html":
        content = re.sub(r"(\b(?:app|event|places|movie)\.js)\?v=[^\"'& ]+", r"\1", content)
        content = re.sub(r"(\b(?:styles|event|places|movie)\.css)\?v=[^\"'& ]+", r"\1", content)
        content = content.replace("<head>", "<head>\n  " + HEAD_MARKER, 1)
    elif suffix == ".css":
        content = CSS_MARKER + "\n" + content
    elif suffix == ".js":
        content = JS_MARKER + "\n" + content
    return content


def files_to_sync():
    return sorted(
        (p for p in MASTER.iterdir()
         if p.is_file() and p.suffix in FRONTEND_EXTENSIONS and p.name not in SKIP_NAMES),
        key=lambda p: p.name,
    )


def run(check: bool = False) -> int:
    source_files = files_to_sync()
    assert source_files and {"index.html", "app.js", "styles.css"} <= {p.name for p in source_files}
    stale = []
    for slug, city in TARGETS.items():
        dest = ROOT / slug
        assert (dest / "data" / "events.json").is_file(), "City-specific event dataset missing: " + slug
        for src in source_files:
            expected = localize(src.read_text(encoding="utf-8"), src.name, city, src.suffix)
            if "אשדוד" in expected or "https://ashdodnet.com" in expected:
                raise AssertionError(f"Unlocalized Ashdod text in {slug}/{src.name}")
            path = dest / src.name
            current = path.read_text(encoding="utf-8") if path.is_file() else None
            if current != expected:
                stale.append(f"{slug}/{src.name}")
                if not check:
                    path.write_text(expected, encoding="utf-8")
    status = "OUT OF SYNC" if check and stale else "UPDATED" if stale else "IN SYNC"
    print(f"Event UI {status}; {len(source_files)} frontend files sourced from Ashdod; "
          f"{len(TARGETS)} target city; {len(stale)} changed files.")
    for path in stale:
        print("  " + path)
    return int(check and bool(stale))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if generated city layouts need an update")
    args = parser.parse_args()
    raise SystemExit(run(check=args.check))

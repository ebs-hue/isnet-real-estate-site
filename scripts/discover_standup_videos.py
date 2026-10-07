#!/usr/bin/env python3
"""Find candidate YouTube clips for stand-up artists not yet in the shared catalog.

Requires YOUTUBE_API_KEY (YouTube Data API v3). Discovery is *not* verification:
write only a review queue, never publish candidates to the live catalog.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "events-preview"
SHARED = BASE / "shared" / "standup-videos.json"
CITIES = ("ashdod", "rishon-lezion")
MIN_NAME_LENGTH = 5

def get_json(url):
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.load(response)

def artist_names(event):
    if event.get("category") != "standup":
        return []
    title = re.sub(r"\s+", " ", str(event.get("title") or "")).strip()
    names = [str(p).strip() for p in event.get("performers", []) if isinstance(p, str)]
    # Stand-up event titles sometimes contain only the comedian's name.
    # Do NOT infer the artist from generic show names or arbitrary first words.
    if 5 <= len(title) <= 35 and not re.search(r"[-–|:]|מופע של|ערב סטנדאפ|פסטיבל|מרתון|קומדי|סטנדאפ עם", title):
        title = re.sub(r"\s+(?:במופע|בסטנדאפ|סטנדאפ).*?$", "", title).strip()
        if len(title.split()) in (2, 3):
            names.append(title)
    return sorted({n for n in names if len(n) >= MIN_NAME_LENGTH})

def main():
    catalog = json.loads(SHARED.read_text(encoding="utf-8"))
    covered = {str(a).strip() for entry in catalog.get("artists", [])
               for a in entry.get("aliases", [entry["name"]])}
    artists = set()
    for city in CITIES:
        path = BASE / city / "data" / "events.json"
        events = json.loads(path.read_text(encoding="utf-8")).get("events", [])
        for event in events:
            if event.get("start_date", "") >= os.environ.get("TODAY", "2026-10-07"):
                artists.update(artist_names(event))
    artists -= covered
    candidates = []
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not key:
        print("YOUTUBE_API_KEY not set; new-artist video discovery is disabled.")
        print("Verified catalog reuse continues to work without a key.")
        return 0
    for artist in sorted(artists)[:30]:
        params = urllib.parse.urlencode({
            "part": "snippet", "type": "video",
            "q": artist + " סטנדאפ ערוץ רשמי", "maxResults": 5,
            "safeSearch": "moderate", "key": key,
        })
        try:
            result = get_json("https://www.googleapis.com/youtube/v3/search?" + params)
        except Exception as exc:
            print(f"Unable to query YouTube for {artist}: {exc}", file=sys.stderr)
            continue
        for item in result.get("items", []):
            vid = item.get("id", {}).get("videoId", "")
            snippet = item.get("snippet", {})
            title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")
            # Candidate generation does not imply the channel is official.
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid) and artist in (title + " " + channel):
                candidates.append({"artist": artist, "youtube_id": vid, "title": title,
                                   "channel": channel, "url": "https://www.youtube.com/watch?v=" + vid,
                                   "review_status": "pending"})
    out = Path(os.getenv("OUTPUT_PATH", "/tmp/standup-review.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"pending_review": candidates}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Discovered {len(candidates)} candidate clips from {len(artists)} uncovered artists.")
    print("Review channel identity, artist identity, embeddability and rights before adding to shared catalog.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

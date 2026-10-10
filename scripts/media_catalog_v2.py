"""ISNET shared media catalogue: reuse, provenance and safe event assignment.

Inspired by ResourceSpace's asset metadata/rights and Directus' file library.
Original implementation; no third-party source code copied.
Storage-agnostic: metadata lives alongside the event engine until a durable
database/object-storage backend is connected. No download, scraping or publish.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit
import re

IMAGE_TYPES = {"event_poster", "artist", "production", "venue", "subcategory", "category"}
RIGHTS = {"verified", "permission_required", "unknown", "expired"}
ASSIGNMENT = {"exact_event", "same_production", "same_artist", "same_venue",
              "subcategory_fallback", "category_fallback"}


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def normalized_asset_url(url: str) -> str:
    parsed = urlsplit(_clean(url))
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Asset URLs must be HTTPS with a valid public hostname")
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"} or parsed.hostname.endswith(".local"):
        raise ValueError("Local URLs are not valid asset sources")
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path, parsed.query, ""))


@dataclass
class MediaAsset:
    asset_id: str
    asset_type: str
    original_url: str
    source_url: str
    title: str = ""
    image_credit: str = ""
    rights_status: str = "unknown"
    licensed_until: str | None = None
    stored_url: str | None = None
    content_sha256: str | None = None
    width: int | None = None
    height: int | None = None
    tags: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    related_event_ids: list[str] = field(default_factory=list)
    source_id: str = ""
    reviewer: str = ""

    def validate(self):
        if self.asset_type not in IMAGE_TYPES or self.rights_status not in RIGHTS:
            raise ValueError("Unsupported asset type or rights status")
        self.original_url = normalized_asset_url(self.original_url)
        self.source_url = normalized_asset_url(self.source_url)
        if self.stored_url:
            self.stored_url = normalized_asset_url(self.stored_url)
        if self.content_sha256 and not re.fullmatch(r"[a-f0-9]{64}", self.content_sha256):
            raise ValueError("Invalid SHA-256 hash")
        if any(n is not None and n <= 0 for n in (self.width, self.height)):
            raise ValueError("Invalid dimensions")
        if self.rights_status == "verified" and not self.reviewer:
            raise ValueError("Verified assets require a reviewer")
        return self


def asset_id_for_url(url: str) -> str:
    return "asset_" + sha256(normalized_asset_url(url).encode()).hexdigest()[:24]


def register_asset(catalog: dict, asset: MediaAsset) -> tuple[dict, bool]:
    """Idempotently register by normalized URL; never silently overwrite review data."""
    asset.validate()
    key = asset_id_for_url(asset.original_url)
    by_id = catalog.setdefault("assets", {})
    for existing in by_id.values():
        if (existing.get("content_sha256") and asset.content_sha256
                and existing["content_sha256"] == asset.content_sha256):
            return existing, False
    if key in by_id:
        return by_id[key], False
    asset.asset_id = key
    record = asdict(asset)
    by_id[key] = record
    return record, True


def publishable(asset: dict, *, on_date: str = "") -> bool:
    """Unknown rights do not become a publication authorization."""
    if asset.get("rights_status") != "verified" or not asset.get("stored_url"):
        return False
    return not (on_date and asset.get("licensed_until") and asset["licensed_until"] < on_date)


def choose_asset(assets: list[dict], event: dict, *, on_date: str = "") -> dict | None:
    """Never match an artist or a production just from the event's category."""
    event_id = str(event.get("event_id") or "")
    production_id = str(event.get("production_id") or "")
    artist_id = str(event.get("artist_id") or "")
    venue_id = str(event.get("venue_id") or "")
    subcategory = str(event.get("subcategory") or "")
    category = str(event.get("category") or "")
    ranked = []
    for asset in assets:
        if not publishable(asset, on_date=on_date):
            continue
        subjects = set(asset.get("subjects") or [])
        event_ids = set(asset.get("related_event_ids") or [])
        typ = asset.get("asset_type")
        rank = (7 if event_id and event_id in event_ids
                else 6 if production_id and f"production:{production_id}" in subjects
                and typ in ("production", "event_poster")
                else 5 if artist_id and f"artist:{artist_id}" in subjects and typ == "artist"
                else 4 if venue_id and f"venue:{venue_id}" in subjects and typ == "venue"
                else 2 if subcategory and f"subcategory:{category}:{subcategory}" in subjects and typ == "subcategory"
                else 1 if category and f"category:{category}" in subjects and typ == "category"
                else 0)
        if rank:
            ranked.append((rank, str(asset.get("asset_id") or ""), asset))
    return max(ranked, key=lambda t: (t[0], t[1]))[2] if ranked else None

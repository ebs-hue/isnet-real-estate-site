"""Internal aliases for labels received from external event sources.

A source label is evidence, not permission to change the public taxonomy.
Exact normalized taxonomy labels resolve deterministically. Other labels are
candidates until an editor verifies the mapping. No AI-inferred mappings are
silently approved.
"""
from __future__ import annotations
from collections import defaultdict
from event_engine_v2 import canonical


def taxonomy_index(taxonomy: dict) -> dict[str, set[tuple[str, str | None]]]:
    index: dict[str, set[tuple[str, str | None]]] = defaultdict(set)
    for category in taxonomy.get("primary_categories", []):
        cat = str(category["id"])
        for value in (cat, category.get("label")):
            if canonical(value):
                index[canonical(value)].add((cat, None))
        for sub in category.get("subcategories", []):
            sub_id = str(sub["id"])
            for value in (sub_id, sub.get("label")):
                if canonical(value):
                    index[canonical(value)].add((cat, sub_id))
    return dict(index)


def match_label(label: str, taxonomy: dict, aliases: dict) -> dict:
    key = canonical(label)
    if not key:
        return {"status": "missing"}
    explicit = aliases.get("approved", {}).get(key)
    if explicit:
        return {"status": "approved_alias", "category": explicit["category"],
                "subcategory": explicit.get("subcategory")}
    matches = taxonomy_index(taxonomy).get(key, set())
    if len(matches) == 1:
        cat, sub = next(iter(matches))
        return {"status": "exact_taxonomy_match", "category": cat, "subcategory": sub}
    return {"status": "needs_review", "reason": "ambiguous" if matches else "new_external_label"}


def collect_alias_candidates(events: list[dict], taxonomy: dict, aliases: dict) -> list[dict]:
    by_key = {}
    for event in events:
        label = str(event.get("source_subcategory") or event.get("source_category") or "").strip()
        result = match_label(label, taxonomy, aliases)
        if result["status"] != "needs_review":
            continue
        key = (canonical(label), str(event.get("source_id") or "unknown"))
        if key not in by_key:
            by_key[key] = {"label": label, "source_id": key[1], "count": 0,
                           "example_titles": [], "status": "review_required"}
        entry = by_key[key]
        entry["count"] += 1
        title = str(event.get("title") or "").strip()
        if title and title not in entry["example_titles"] and len(entry["example_titles"]) < 3:
            entry["example_titles"].append(title)
    return sorted(by_key.values(), key=lambda x: (-x["count"], x["source_id"], x["label"]))

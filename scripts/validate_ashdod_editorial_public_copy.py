#!/usr/bin/env python3
"""Fail closed on internal editorial notes in staged public event copy.

Read-only. This validator never publishes and never changes event statuses.
"""
import json
import re
import sys
from pathlib import Path

BLOCKED = [
    r"(?i)https?://", r"(?i)source[_ ]url", r"(?i)editorial[_ ]questions",
    r"לפי (?:עמוד|אתר|מקור|הפרסום|המידע)", r"על פי (?:עמוד|אתר|מקור|הפרסום|המידע)",
    r"יש (?:לבדוק|לאמת|לעיין|לברר)", r"נדרש בירור", r"לא ניתן לאמת",
    r"העמוד אינו מפרט", r"המקור אינו מפרט", r"לא מצוין (?:במקור|באתר)",
    r"פרטים.*(?:באתר ההרשמה|בעמוד ההרשמה|בעמוד המקור)",
    r"שים לב", r"ייתכן ש", r"הסבירות גבוהה", r"(?i)content_ready_for_media",
]
PUBLIC_FIELDS = ("public_description", "short_pitch")

def validate(event):
    problems = []
    for field in PUBLIC_FIELDS:
        value = event.get(field)
        if not isinstance(value, str) or len(value.strip()) < 35:
            problems.append(f"{field}: empty/too short")
            continue
        for pattern in BLOCKED:
            if re.search(pattern, value):
                problems.append(f"{field}: forbidden pattern {pattern}")
    return problems

def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else
        "events-preview/admin/data/editorial-review-ashdod-2026-10-10.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    failures = {e.get("event_id", "unknown"): validate(e) for e in data["events"]}
    failures = {k: v for k, v in failures.items() if v}
    print(json.dumps({"checked": len(data["events"]), "failed": failures}, ensure_ascii=False))
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())

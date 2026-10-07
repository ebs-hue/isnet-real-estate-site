#!/usr/bin/env python3
"""Small offline regression suite for the two-city public calendar readers."""
from pathlib import Path
import importlib.util
from bs4 import BeautifulSoup

s = importlib.util.spec_from_file_location("events", Path(__file__).with_name("sync_events_from_sources.py"))
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)

base = {"name":"sample","url":"https://ashdod.smarticket.co.il/","venue":"אשדוד","source_type":"official","parser":"smarticket"}
html = """<main><a href="מופע_חדש/?id=11"><img src="/uploads/poster.jpg" alt="מופע לילדים"><div>06 אוקטובר מופע לילדים פרטים נוספים
מופע לילדים המשכן לאמנויות הבמה אשדוד ביום שלישי, 6 באוקטובר 2026 בשעה 17:30
</div></a><a href="סתם">לוח אירועים</a></main>"""
rows = m.smarticket_rows(BeautifulSoup(html, "html.parser"), base)
assert len(rows) == 1, rows
assert rows[0]["start_date"] == "2026-10-06", rows
assert rows[0]["start_time"] == "17:30", rows
assert rows[0]["ticket_url"] == "https://ashdod.smarticket.co.il/מופע_חדש/?id=11", rows
assert rows[0]["image_url"] == "https://ashdod.smarticket.co.il/uploads/poster.jpg", rows
assert rows[0]["image_rights_status"] == "needs_review", rows
assert rows[0]["image_publishable"] is False, rows

source = {"name":"htrl","url":"https://htrl.co.il/לוח-שנה/","venue":"היכל התרבות מאיר ניצן","source_type":"official","parser":"htrl"}
html = "<div>אודי כגן</div><div>08.01.27</div><div>21:30</div><div>שישי</div><div>היכל התרבות</div><a>רכישה</a>"
rows = m.htrl_rows(BeautifulSoup(html,"html.parser"),source)
assert len(rows) == 1, rows
assert rows[0]["start_date"] == "2027-01-08", rows
assert rows[0]["title"] == "אודי כגן", rows

source = {"name":"kotar_rishon","url":"https://www.kotar-rishon-lezion.org.il/events-category/eventsactivities/",
          "venue":"רשת הספריות ראשון לציון","source_type":"official","parser":"kotar"}
html = """<div>08.10.2026</div><div>כותר טף - הצגות והפעלות</div>
<div>string(73) "הפינה של גלי - פעילות מוזיקאלית לקטנטנים"</div>
<div>bool(true)</div><div>הפינה של גלי - פעילות מוזיקאלית לקטנטנים</div>
<div>גילאים:</div><div>0-3</div><div>שעות:</div><div>11:00 - 11:25</div>
<div>מיקום:</div><div>אחד העם 7, ראשון לציון</div>"""
rows = m.kotar_rows(BeautifulSoup(html,"html.parser"),source)
assert len(rows) == 1, rows
assert rows[0]["start_time"] == "11:00", rows

ld = '<script type="application/ld+json">{"@type":"Event","name":"ערב שירה מקומית","startDate":"2026-11-06T20:30:00+02:00","image":"https://ashdod.smarticket.co.il/uploads/song.jpg","location":{"name":"אולם דיונה אשדוד"}}</script>'
rows = m.generic_jsonld_rows(BeautifulSoup(ld, "html.parser"),base)
assert len(rows) == 1 and rows[0]["start_date"] == "2026-11-06", rows
assert rows[0]["image_url"].endswith("/uploads/song.jpg"), rows

assert m.event_key({"title":"ערב שירה – מקומית","start_date":"2026-11-06","start_time":"20:30"}) == m.event_key({"title":"ערב שירה - מקומית","start_date":"2026-11-06","start_time":"20:30"})

original = {"city":"אשדוד","title":"מופע חגיגי","start_date":"2026-10-10",
            "start_time":"17:00","ticket_url":"https://ashdod.smarticket.co.il/",
            "sources":[{"name":"ashdod_smarticket"}],"venue":"היכל התרבות"}
second = dict(original, start_time="21:00")
assert m.existing_match([original], second, "ashdod_smarticket") is None, "Distinct showtimes must not overwrite each other"

original_ticket = dict(original, ticket_url="https://ashdod.smarticket.co.il/מופע?id=100")
changed = dict(original_ticket, start_date="2026-10-11", start_time="18:00")
assert m.existing_match([original_ticket], changed, "ashdod_smarticket") is original_ticket, "Exact ticket ID may confirm a reschedule"

manual = dict(original, event_id="manual123")
dupe = dict(original, event_id="auto_as_a1", title="מופע חגיגי | היכל התרבות אשדוד",
            sources=[{"name":"ashdod_smarticket"}])
entries=[dupe,manual]
invalid, removed = m.clean_generated_duplicates(entries)
assert len(entries)==1 and entries[0]["event_id"]=="manual123" and removed==1, entries


adult_source = {"name":"htrl_adults","url":"https://htrl.co.il/third-calendar/",
                "venue":"לגלות תרבות, ראשון לציון","source_type":"official","parser":"htrl"}
adult_html = """<div>שפת הגוף התנכ״ית</div><div>10.10.26</div><div>18:00</div>
<div>שבת</div><div>בית יד לבנים</div><div>רכישה</div>
<div>רצח רבין- כרוניקה של כישלון מבצעי</div><div>11.11.26</div>
<div>00:11</div><div>רביעי</div><div>אודיטוריום היכל התרבות</div>"""
adult_rows = m.htrl_rows(BeautifulSoup(adult_html,"html.parser"), adult_source)
assert len(adult_rows)==1, adult_rows
assert adult_rows[0]["venue"]=="בית יד לבנים, ראשון לציון", adult_rows
assert adult_rows[0]["audiences"] == ["adults"]


collision = [
    {"event_id":"auto_ri_abc","city":"ראשון לציון","title":"שירה",
     "start_date":"2026-10-06","start_time":"18:00","venue":"בית העם","ticket_url":""},
    {"event_id":"auto_ri_abc","city":"ראשון לציון","title":"תיאטרון",
     "start_date":"2026-10-06","start_time":"19:00","venue":"מוזיאון ראשון","ticket_url":""}
]
assert m.fix_imported_id_collisions(collision)==1
assert len({x["event_id"] for x in collision})==2, collision

print("PASS: Smarticket Hebrew dates, HTRL, Kotar, JSON-LD, stable dedupe")

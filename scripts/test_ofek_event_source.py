#!/usr/bin/env python3
"""Offline tests: publish only Ofek entries with matching verified dates/hours."""
from datetime import date
from pathlib import Path
import importlib.util
from bs4 import BeautifulSoup

path = Path(__file__).with_name("ofek_event_source.py")
spec = importlib.util.spec_from_file_location("ofek_event_source", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

root = "https://www.ofek-ashdod.org.il/"
source = {"name":"ofek_ashdod","url":root+"page.php?type=events",
          "listing_pages":[],"parser":"ofek"}
soup = BeautifulSoup("""
<h2>אירועים קרובים</h2>
<a href="/page.php?type=event&id=33651">סיור טעימות ואתרים באשדוד 01/06/2027 - 01/06/2027</a>
<a href="/page.php?type=event&id=33652">סיור דוגמה נוסף - 02/06/2027</a>
<a href="/page.php?type=event&id=30001">טיול ישן - 05/09/2025</a>
<a href="https://www.example.com/page.php?type=event&id=25">קישור חיצוני - 05/11/2026</a>
""","html.parser")

detail = BeautifulSoup("""
<h2>סיור טעימות ואתרים באשדוד 01/06/2027</h2>
<p>תאריך לועזי יום שלישי, 01/06/2027</p>
<p>שעה 07:20</p>
<div>מיקום חיצוני</div><p>מחיר: ₪140.00</p>
""","html.parser")
wrong_date = BeautifulSoup("""
<h2>סיור דוגמה נוסף</h2><p>תאריך לועזי יום ראשון, 04/06/2027</p><p>שעה 11:00</p>
""","html.parser")

calls=[]
def fetch_once(spec):
    calls.append(spec["url"])
    return (detail if spec["url"].endswith("id=33651") else wrong_date),None

rows=module.extract_ofek_events(soup,source,fetch_once,today=date(2026,10,6),sleep=0)
assert len(rows)==1, rows
e=rows[0]
assert e["start_date"]=="2027-06-01" and e["start_time"]=="07:20"
assert e["category"]=="tour" and e["audiences"]==["adults"]
assert e["price_min_ils"]==140
assert e["ticket_url"]=="https://www.ofek-ashdod.org.il/page.php?type=event&id=33651"
assert len(calls)==2,calls
assert not module.safe_link("https://not-ofek.com/page.php?type=event&id=11",root)
print("PASS: Ofek verified future events, activity type, price, date mismatch exclusion, allowlist")

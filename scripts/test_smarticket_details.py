#!/usr/bin/env python3
"""Offline regression: Smarticket details are accepted only from an exact event page."""
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup

p=Path(__file__).with_name("enrich_smarticket_event_details.py")
spec=importlib.util.spec_from_file_location("smarticket_meta",p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

original={
    "title":"הרצאה של יונתן סררו","start_date":"2026-10-11",
    "ticket_url":"https://ashdod.smarticket.co.il/%D7%94%D7%A8%D7%A6%D7%90%D7%94_%D7%A9%D7%9C_%D7%99%D7%95%D7%A0%D7%AA%D7%9F_%D7%A1%D7%A8%D7%A8%D7%95/?id=17695",
    "sources":[{"name":"ashdod_smarticket"}],
}
assert mod.source_detail_url(original,"ashdod") == original["ticket_url"]
assert mod.source_detail_url({**original,"ticket_url":"https://example.org/?id=17695"},"ashdod") is None

html="""<main><h1>הרצאה של יונתן סררו</h1>
<p>מרכז קהילתי ספרא-רח' אב 4 אשדוד</p>
<a href="https://maps.google.com/?q=%D7%A8%D7%97%27">מפת הגעה</a>
<p>ביום ראשון, 11 באוקטובר 2026 18:00 - 19:30</p>
<p>משך: שעה ו-30 דקות</p><p>מחיר 20 ₪</p><p>הכרטיסים אזלו</p>
</main>"""
soup=BeautifulSoup(html,"html.parser")
detail=mod.detail_facts(soup,original)
assert "ספרא" in detail["venue"],detail
assert detail["address"].endswith("אשדוד"),detail
assert detail["price_min_ils"]==20 and detail["price_max_ils"]==20,detail
assert detail["ticket_status"]=="sold_out",detail
assert detail["duration_minutes"]==90,detail
assert detail["ticket_provider"]=="החברה העירונית לתרבות ופנאי באשדוד",detail
wrong=BeautifulSoup(html.replace("11 באוקטובר 2026","12 באוקטובר 2026"),"html.parser")
assert mod.detail_facts(wrong,original)=={}, "Different date must not contaminate record"
wrong_title=BeautifulSoup(html.replace("הרצאה של יונתן סררו","הרצאה אחרת"),"html.parser")
assert mod.detail_facts(wrong_title,original)=={}, "Different event must not contaminate record"
print("PASS: Smarticket date/title match, address, price, duration and sold-out status")

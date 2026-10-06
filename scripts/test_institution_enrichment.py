#!/usr/bin/env python3
"""Regression: preserve locations across unrelated organizer events."""
import importlib.util
from pathlib import Path

root=Path(__file__).resolve().parents[1]
path=root/"scripts"/"enrich_events_institutions.py"
spec=importlib.util.spec_from_file_location("institutions", path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
import json

a=json.loads((root/"events-preview/ashdod/data/institutions.json").read_text())["institutions"]
r=json.loads((root/"events-preview/rishon-lezion/data/institutions.json").read_text())["institutions"]

lecture={"title":"היסטוריה ואמנות","venue":"מרכז מונארט, אשדוד",
         "sources":[{"name":"ofek_ashdod"}],"city":"אשדוד"}
m.apply_registry(lecture,a)
assert lecture["operator_id"]=="ofek_ashdod",lecture
assert lecture["venue_institution_id"]=="monart_ashdod",lecture
assert lecture["address"]=="דרך ארץ 8, אשדוד",lecture
assert lecture["contact_phone"]=="08-9238680",lecture
assert lecture["venue_phone"]=="08-8545170",lecture
assert lecture["organizer"]=="הקתדרה העממית אופק",lecture
assert m.apply_registry(lecture,a)==0,"Repeated ingestion must be idempotent"

tour={"title":"טיול בצפון","venue":"יציאה לסיור מטעם קתדרת אופק, אשדוד",
      "sources":[{"name":"ofek_ashdod"}],"city":"אשדוד"}
m.apply_registry(tour,a)
assert tour["operator_id"]=="ofek_ashdod"
assert not tour.get("address"),"Organizer's office must not be assigned as tour departure location"
assert tour["contact_phone"]=="08-9238680"

safra={"title":"הרצאה של יונתן סררו","venue":"מרכז קהילתי ספרא, אשדוד",
       "address":"רחוב אב 4, אשדוד","contact_phone":"08-8675261",
       "sources":[{"name":"ashdod_smarticket"}],"city":"אשדוד"}
m.apply_registry(safra,a)
assert safra["contact_phone"]=="08-8675261" and safra["address"]=="רחוב אב 4, אשדוד"
assert safra["venue_institution_id"]=="ironit_safra"

mishkan={"title":"מחזמר","venue":"המשכן לאמנויות הבמה אשדוד","city":"אשדוד",
         "sources":[{"name":"mishkan_smarticket"}]}
m.apply_registry(mishkan,a)
assert mishkan["address"]=="דרך ארץ 1, אשדוד" and mishkan["contact_phone"]=="*5359",mishkan

adult={"title":"הרצאה על אמנות","venue":"בית העם, ראשון לציון","city":"ראשון לציון",
       "sources":[{"name":"htrl_adults"}]}
m.apply_registry(adult,r)
assert adult["operator_id"]=="htrl_adults", adult
assert adult["address"]=="זד״ל 3, ראשון לציון","Matched venue must supply its own verified address, not HTRL office"
assert adult["venue_institution_id"]=="rishon_beit_haam"
unknown={"title":"מפגש במקום משתנה","venue":"אתר משתנה ללא כתובת מאומתת","city":"ראשון לציון","sources":[{"name":"htrl_adults"}]}
m.apply_registry(unknown,r)
assert unknown["operator_id"]=="htrl_adults" and not unknown.get("address"),"Organizer office must not be used for unknown venue"

museum={"title":"תערוכה","venue":"מוזיאון אגם","city":"ראשון לציון",
        "sources":[{"name":"yama"}]}
m.apply_registry(museum,r)
assert museum["address"].startswith("מיש״ר 1") and museum["contact_phone"]=="03-5555900",museum
print("PASS: source identity, matched venue contacts, organizer/venue isolation, no address guesses, idempotence")

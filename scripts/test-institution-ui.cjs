#!/usr/bin/env node
// Safe smoke tests for shared organizer pages and lecture artwork.
const fs=require("node:fs"),assert=require("node:assert/strict");
const base="events-preview";
const load=(city,name)=>fs.readFileSync(base+"/"+city+"/"+name,"utf8");
for(const city of ["ashdod","rishon-lezion"]){
 const registry=JSON.parse(load(city,"data/institutions.json"));
 const events=JSON.parse(load(city,"data/events.json")).events;
 const operator=load(city,"operator.html"),index=load(city,"index.html");
 const ids=registry.institutions.map(x=>x.id);
 assert.equal(ids.length,new Set(ids).size);
 assert.ok(operator.includes('id="contactDetails"')&&operator.includes('id="operatorEvents"'));
 assert.ok(index.includes('id="operatorStrip"'));
 assert.ok(index.includes('operator.html?id='));
 assert.ok(operator.includes('data/institutions.json'));
 assert.ok(index.includes("איור להמחשה"),"Distinct fallback designs must be clearly labeled");
 for(const org of registry.institutions.filter(x=>x.featured)){
  const results=events.filter(e=>e.operator_id===org.id||
   (e.sources||[]).some(src=>(org.source_names||[]).includes(src.name)));
  assert.ok(results.length>0,"No source events for "+org.id);
 }
 for(const e of events)assert.ok((e.sources||[]).length,"Missing source in "+city);
}
const ash=JSON.parse(load("ashdod","data/events.json")).events;
const ofek=ash.filter(e=>e.operator_id==="ofek_ashdod");
assert.ok(ofek.length>=20,"Ofek must remain indexed");
assert.ok(ofek.some(e=>e.category==="tour"),"Ofek excursions must also be tours");
assert.ok(ofek.some(e=>e.category==="lecture"),"Ofek talks must also be lectures");
assert.ok(!ofek.some(e=>e.category==="workshop"||e.category==="classes"),"Workshops and classes must not be published on the event board");
for(const e of ofek){
 assert.ok(e.contact_phone,"Ofek office phone missing");
 if(e.category==="tour"&&e.venue?.includes("יציאה לסיור"))
  assert.ok(!e.address,"Do not use Ofek office as tour departure address");
}
const app=load("ashdod","app.js");
assert.ok(app.includes("lectureFallbackTopic(e)"),"Topic matching must exist");
assert.ok(app.includes('class="category-fallback lectureArtwork"'));
const details=load("ashdod","event.js");
assert.ok(details.includes("operator.html?id="),"Event detail must navigate to operator");
assert.ok(details.includes("טלפון המקום"),"Venue-specific contact must be exposed");
console.log("PASS: 2 cities, organizer pages, lecture artwork, "+ofek.length+" Ofek events, contact integrity");

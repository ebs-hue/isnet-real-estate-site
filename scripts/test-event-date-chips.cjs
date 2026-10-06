#!/usr/bin/env node
// Regression test for 5 desktop / 4 mobile dates without losing schedule data.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("events-preview/ashdod/app.js","utf8");
const css = fs.readFileSync("events-preview/ashdod/styles.css","utf8");
const from = source.indexOf("function dateChipHTML(e){");
const to = source.indexOf("\nfunction scheduleSummary", from);
assert.ok(from >= 0 && to > from, "dateChipHTML exists");
assert.match(source,/dateStack__more.*?\)\)return/);
const state = {date:null};
const all = Array.from({length:18}, (_,i)=>({start_date:"2026-10-"+String(i+6).padStart(2,"0")}));
const ctx={
  state,
  uniqueOccurrenceDates: ()=> all,
  localDate: s=>new Date(s+"T12:00:00Z"),
  escapeHtml: s=>String(s).replace(/&/g,"&amp;").replace(/"/g,"&quot;"),
  Intl,
  encodeURIComponent
};
vm.createContext(ctx);
vm.runInContext(source.slice(from,to),ctx);
for(const n of [1,4,5,6,18]){
  const rendered = ctx.dateChipHTML({event_id:"testing 7", start_date:all[0].start_date});
  assert.equal((rendered.match(/class="multiDateChip/g)||[]).length, 5, "five date chips before viewport styling");
  assert.ok(rendered.includes('event.html?id=testing%207#dates'), "full schedule link");
  assert.ok(rendered.includes('עוד 13 מועדים'), "desktop remainder");
  assert.ok(rendered.includes('עוד 14 מועדים'), "mobile remainder");
}
ctx.uniqueOccurrenceDates=()=>all.slice(0,4);
const four=ctx.dateChipHTML({event_id:"four",start_date:all[0].start_date});
assert.equal((four.match(/class="multiDateChip/g)||[]).length,4);
assert.ok(!four.includes("dateStack__more--desktop") && !four.includes("dateStack__more--mobile"));
ctx.uniqueOccurrenceDates=()=>all.slice(0,5);
const five=ctx.dateChipHTML({event_id:"five",start_date:all[0].start_date});
assert.ok(!five.includes("dateStack__more--desktop") && five.includes("עוד 1 מועדים"));
ctx.uniqueOccurrenceDates=()=>all.slice(0,1);
const one=ctx.dateChipHTML({event_id:"single",start_date:all[0].start_date});
assert.ok(one.includes('class="dateChip"')&&!one.includes("dateStack__more"));
assert.match(css,/\.multiDateChip:nth-child\(5\)\{display:none\}/);
assert.match(css,/\.dateStack__more--mobile\{display:flex\}/);
console.log("PASS: single, 4, 5 and 18 dates; mobile cap; full detail link");

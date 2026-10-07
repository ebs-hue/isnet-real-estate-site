const TODAY="2026-10-07";
const categoryLabels={music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים",theatre:"תיאטרון",lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה",sport:"ספורט",tour:"סיורים",other:"אחר"};
const cityConfig=[
  {slug:"ashdod",name:"אשדוד",base:"../ashdod/"},
  {slug:"rishon-lezion",name:"ראשון לציון",base:"../rishon-lezion/"}
];
let all=[];
const LOCAL_OVERRIDES_KEY="isnet-event-overrides";
const LOCAL_NEW_KEY="isnet-new-events";

const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function fmtDate(s){if(!s)return"—";const [y,m,d]=s.split("-");return d+"/"+m+"/"+y}
function editorialEntry(editorial,id){return editorial?.events?.[id]||{}}
function readJson(key,fallback){try{return JSON.parse(localStorage.getItem(key)||"")||fallback}catch{return fallback}}
function localOverrides(){return readJson(LOCAL_OVERRIDES_KEY,{})}
function localNewEvents(){return readJson(LOCAL_NEW_KEY,[])}
function applyLocalOverride(e){
  const patch=localOverrides()[e._citySlug+":"+e.event_id];
  return patch?{...e,...patch,_localOverride:true}:e;
}
function artistVideoFor(event,catalog){
  if(event.category!=="standup")return null;
  const title=String(event.title||"").normalize("NFKC");
  return (catalog?.artists||[]).find(a=>a.video_verified===true&&(a.aliases||[a.name]).some(alias=>title.includes(String(alias).normalize("NFKC"))))||null;
}
function issuesFor(e){
  const issues=[];
  if(!e._description)issues.push({key:"needs_content",label:"חסר תוכן",level:"warn"});
  if(!(e.image_publishable===true&&e.image_verified===true&&(e.thumbnail_url||e.image_url)))issues.push({key:"needs_image",label:"תמונה",level:"bad"});
  if(e.category==="standup"&&!e._video)issues.push({key:"needs_video",label:"וידאו",level:"warn"});
  if(!(e.purchase_url||e.ticket_url||e.purchase_phone))issues.push({key:"needs_ticket",label:"פעולה",level:"warn"});
  return issues;
}
async function load(){
  $("resultCount").textContent="טוען נתונים...";
  const shared=await fetch("../shared/standup-videos.json",{cache:"no-store"}).then(r=>r.ok?r.json():{artists:[]}).catch(()=>({artists:[]}));
  const groups=await Promise.all(cityConfig.map(async city=>{
    const [data,editorial]=await Promise.all([
      fetch(city.base+"data/events.json",{cache:"no-store"}).then(r=>r.json()),
      fetch(city.base+"data/editorial.json",{cache:"no-store"}).then(r=>r.ok?r.json():{events:{}}).catch(()=>({events:{}}))
    ]);
    return (data.events||[]).map(e=>{
      const ed=editorialEntry(editorial,e.event_id);
      const video=e.youtube_id||(ed.video_verified===true&&ed.youtube_id)||artistVideoFor(e,shared)?.youtube_id||null;
      const description=ed.long_description||e.long_description||ed.short_pitch||e.series_description||e.description||"";
      return {...e,_citySlug:city.slug,_cityBase:city.base,_description:description,_video:video,_issues:null};
    });
  }));
  const persisted=groups.flat().map(applyLocalOverride);
  const local=localNewEvents().map(e=>({...e,_localNew:true,_cityBase:e._citySlug==="ashdod"?"../ashdod/":"../rishon-lezion/"}));
  all=[...persisted,...local].map(e=>({...e,_issues:issuesFor(e)}));
  buildFilters();render();
}
function buildFilters(){
  const cities=[...new Set(all.map(e=>e.city).filter(Boolean))].sort();
  $("city").innerHTML='<option value="">כל הערים</option>'+cities.map(x=>'<option>'+esc(x)+'</option>').join("");
  const cats=[...new Set(all.map(e=>e.category).filter(Boolean))].sort((a,b)=>(categoryLabels[a]||a).localeCompare(categoryLabels[b]||b,"he"));
  $("category").innerHTML='<option value="">כל הקטגוריות</option>'+cats.map(x=>'<option value="'+esc(x)+'">'+esc(categoryLabels[x]||x)+'</option>').join("");
}
function filtered(){
  const q=$("q").value.trim().toLowerCase(),city=$("city").value,cat=$("category").value,status=$("status").value,quality=$("quality").value;
  return all.filter(e=>{
    if(city&&e.city!==city)return false;
    if(cat&&e.category!==cat)return false;
    if(status==="active"&&(e.status!=="active"||e.start_date<TODAY))return false;
    if(status==="expired"&&(e.status!=="active"||e.start_date>=TODAY))return false;
    if(["draft","hidden","archived","trashed"].includes(status)&&e.status!==status)return false;
    if(quality==="clean"&&e._issues.length)return false;
    if(quality&&quality!=="clean"&&!e._issues.some(i=>i.key===quality))return false;
    if(q){
      const hay=[e.title,e.venue,e.category,categoryLabels[e.category],e.event_id,e.organizer,e.city].filter(Boolean).join(" ").toLowerCase();
      if(!hay.includes(q))return false;
    }
    return true;
  }).sort((a,b)=>(b.start_date+(b.start_time||"")).localeCompare(a.start_date+(a.start_time||"")));
}
function renderStats(){
  const active=all.filter(e=>e.start_date>=TODAY);
  const stats=[
    [all.length,"כל האירועים","כולל טיוטות מקומיות"],
    [active.filter(e=>e.status==="active").length,"אירועים עתידיים","פעילים מהיום והלאה"],
    [active.filter(e=>!e._description).length,"חסר תוכן","דורש העשרה"],
    [active.filter(e=>e._issues.some(i=>i.key==="needs_image")).length,"בעיית תמונה","חסרה או לא מאושרת"],
    [active.filter(e=>e.category==="standup"&&!e._video).length,"סטנדאפ בלי וידאו","משימת מדיה"]
  ];
  $("summary").innerHTML=stats.map(([n,t,s])=>'<article class="stat"><strong>'+n+'</strong><span>'+t+'</span><small>'+s+'</small></article>').join("");
}
function render(){
  renderStats();
  const rows=filtered();
  $("resultCount").textContent=rows.length+" אירועים מוצגים מתוך "+all.length;
  $("empty").hidden=rows.length>0;
  $("rows").innerHTML=rows.slice(0,500).map(e=>{
    const rawImg=e.thumbnail_url||e.image_url||"";
    const img=rawImg ? (/^(https?:|data:)/.test(rawImg)?rawImg:e._cityBase+rawImg) : "";
    const imageApproved=Boolean(rawImg&&e.image_publishable===true&&e.image_verified===true);
    const imageStatus=!rawImg
      ? '<span class="tag bad">אין תמונה</span>'
      : imageApproved
        ? '<span class="tag good">יש תמונה · מאושרת</span>'
        : '<span class="tag warn">יש תמונה · לבדיקה</span>';
    const src=(e.sources||[])[0]?.name||e.purchase_source||"—";
    const issues=e._issues.length?e._issues.map(i=>'<span class="tag '+i.level+'">'+esc(i.label)+'</span>').join(""):'<span class="tag good">תקין</span>';
    const url=e._cityBase+"event.html?id="+encodeURIComponent(e.event_id);
    const editUrl=(e._localNew?"new.html?edit=1&city=":"edit.html?city=")+encodeURIComponent(e._citySlug)+"&id="+encodeURIComponent(e.event_id);
    const statusLabel=e.status==="draft"?"טיוטה":e.status==="hidden"?"מוסתר":e.status==="archived"?"ארכיון":e.status==="trashed"?"בסל":"";
    const promotionLabel=e.promotion==="promoted"?"מקודם":e.promotion==="recommended"?"מומלץ":"רגיל";
    const promotionClass=e.promotion==="promoted"?"promotion-promoted":e.promotion==="recommended"?"promotion-recommended":"promotion-normal";
    return '<tr>'+
      '<td><div class="event-cell">'+(img?'<img class="thumb" src="'+esc(img)+'" alt="">':'<div class="thumb"></div>')+
      '<div><div class="event-name">'+esc(e.title)+'</div><div class="event-id">'+esc(e.event_id)+'</div>'+(statusLabel?'<span class="status-chip status-'+esc(e.status)+'">'+esc(statusLabel)+'</span>':'')+'</div></div></td>'+
      '<td class="image-status">'+imageStatus+'</td>'+
      '<td>'+esc(e.city)+'</td><td><span class="tag">'+esc(categoryLabels[e.category]||e.category||"—")+'</span></td>'+
      '<td>'+esc(fmtDate(e.start_date))+(e.start_time?'<br><small>'+esc(e.start_time)+'</small>':'')+'</td>'+
      '<td>'+esc(e.venue||"—")+'</td><td><div class="issues">'+issues+'</div></td>'+
      '<td><span class="promotion-chip '+promotionClass+'">'+promotionLabel+'</span></td>'+
      '<td class="source" title="'+esc(src)+'">'+esc(src)+'</td>'+
      '<td><a class="link" href="'+esc(url)+'" target="_blank" rel="noopener">פתח ↗</a></td>'+
      '<td><a class="edit-link" href="'+esc(editUrl)+'">עריכה ✎</a></td>'+
      '</tr>';
  }).join("");
}
["q","city","category","status","quality"].forEach(id=>$(id).addEventListener("input",render));
$("clearBtn").addEventListener("click",()=>{["q","city","category","status","quality"].forEach(id=>$(id).value="");render()});
$("refreshBtn").addEventListener("click",load);
load().catch(err=>{$("resultCount").textContent="שגיאה בטעינת הנתונים";console.error(err)});

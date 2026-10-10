const TODAY="2026-10-07";
let taxonomyCategories=[];
const categoryLabels={music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים",theatre:"תיאטרון",lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה",sport:"ספורט",seniors:"הגיל השלישי וגמלאים",other:"אחר"};
const cityConfig=[
  {slug:"ashdod",name:"אשדוד",base:"../ashdod/"},
  {slug:"rishon-lezion",name:"ראשון לציון",base:"../rishon-lezion/"}
];
let all=[];
let analytics={generated_at:null,views_7d:{},views_30d:{},views_all:{}};
const LOCAL_OVERRIDES_KEY="isnet-event-overrides";
const LOCAL_NEW_KEY="isnet-new-events";

const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function fmtDate(s){if(!s)return"—";const [y,m,d]=s.split("-");return d+"/"+m+"/"+y}
function horizonEnd(){
  const d=new Date(); d.setHours(0,0,0,0); d.setMonth(d.getMonth()+5);
  return [d.getFullYear(),String(d.getMonth()+1).padStart(2,"0"),String(d.getDate()).padStart(2,"0")].join("-");
}
function editorialEntry(editorial,id){return editorial?.events?.[id]||{}}
function readJson(key,fallback){try{return JSON.parse(localStorage.getItem(key)||"")||fallback}catch{return fallback}}
function localOverrides(){return readJson(LOCAL_OVERRIDES_KEY,{})}
function localNewEvents(){return readJson(LOCAL_NEW_KEY,[])}
function applyLocalOverride(e){
  const patch=localOverrides()[e._citySlug+":"+e.event_id];
  return patch?{...e,...patch,_localOverride:true}:e;
}
function mergeDbRecordWithFreshMedia(e,db){
  if(!db?.payload)return e;
  const merged={...e,...db.payload,_dbRecord:true};
  const manualImage=Boolean(db.payload.image_manual_override===true);
  if(!manualImage){
    const mediaFields=[
      "image_url","thumbnail_url","thumbnail_ready","image_origin_url","image_source",
      "image_credit","image_publishable","image_verified","image_rights_status",
      "image_strategy","image_represents_event","image_represents_category",
      "media_bank_id","thumbnail_source"
    ];
    for(const key of mediaFields){
      if(Object.prototype.hasOwnProperty.call(e,key)) merged[key]=e[key];
      else delete merged[key];
    }
  }

  // Fresh feed classification wins over stale CMS snapshots unless an editor
  // explicitly locked a manual category override.
  const manualCategory=Boolean(db.payload.category_manual_override===true);
  if(!manualCategory){
    if(Object.prototype.hasOwnProperty.call(e,"category")) merged.category=e.category;
    else delete merged.category;
    for(const key of ["category_previous","category_review_status","category_review_confidence","category_reviewed_at"]){
      if(Object.prototype.hasOwnProperty.call(e,key)) merged[key]=e[key];
      else delete merged[key];
    }
  }
  return merged;
}
function artistVideoFor(event,catalog){
  if(event.category!=="standup")return null;
  const title=String(event.title||"").normalize("NFKC");
  return (catalog?.artists||[]).find(a=>a.video_verified===true&&(a.aliases||[a.name]).some(alias=>title.includes(String(alias).normalize("NFKC"))))||null;
}
function hasEditorialNote(text){
  return /העמוד אינו מפרט|המקור אינו מפרט|יש לבדוק|יש לאמת|נדרש בירור|לא ניתן לאמת|לפי עמוד האירוע|על פי אתר|לפי אתר|פרטים נוספים.*מקור|לא ברור מן המקור|מומלץ לבדוק|כדאי לבדוק/.test(String(text||""));
}
function issuesFor(e){
  const issues=[];
  const desc=String(e._description||e.long_description||e.event_summary||e.short_pitch||"");
  if(!desc.trim())issues.push({key:"needs_content",label:"חסר תוכן",level:"warn"});
  else if(hasEditorialNote(desc))issues.push({key:"needs_content",label:"הערת מערכת בתוכן",level:"bad"});
  else if(desc.trim().length<160)issues.push({key:"needs_content",label:"תוכן דל",level:"warn"});
  if(!(e.image_publishable===true&&e.image_verified===true&&(e.thumbnail_url||e.image_url)))issues.push({key:"needs_image",label:"תמונה",level:"bad"});
  const taxonomy=taxonomyCategories.find(cat=>cat.id===e.category);
  if(taxonomy?.subcategories?.length && !taxonomy.subcategories.some(sub=>sub.id===e.subcategory)){
    issues.push({key:"needs_subcategory",label:"חסרה תת־קטגוריה",level:"warn"});
  }
  if(e.category==="standup"&&!e._video)issues.push({key:"needs_video",label:"וידאו",level:"warn"});
  if(!(e.purchase_url||e.ticket_url||e.purchase_phone))issues.push({key:"needs_ticket",label:"פעולה",level:"warn"});
  return issues;
}
async function load(){
  const taxonomyResponse=await fetch("data/taxonomy.json",{cache:"no-store"});
  if(!taxonomyResponse.ok)throw Error("taxonomy unavailable");
  taxonomyCategories=(await taxonomyResponse.json()).primary_categories||[];
  for(const item of taxonomyCategories)categoryLabels[item.id]=item.label;
  $("resultCount").textContent="טוען נתונים...";
  const [shared,analyticsData]=await Promise.all([
    fetch("../shared/standup-videos.json",{cache:"no-store"}).then(r=>r.ok?r.json():{artists:[]}).catch(()=>({artists:[]})),
    fetch("data/event-analytics.json",{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null)
  ]);
  if(analyticsData) analytics=analyticsData;
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
  const dbRecords=await (window.ISNET_DB?.listEventRecords?.()||Promise.resolve([]));
  const dbMap=new Map(dbRecords.map(r=>[r.city_slug+":"+r.event_id,r]));
  const persisted=groups.flat().map(e=>{
    const db=dbMap.get(e._citySlug+":"+e.event_id);
    if(db?.payload)return mergeDbRecordWithFreshMedia(e,db);
    return applyLocalOverride(e);
  });
  const dbManual=dbRecords.filter(r=>r.record_type==="manual").map(r=>{
    const e={...(r.payload||{}),event_id:r.event_id,_citySlug:r.city_slug,_dbRecord:true,_localNew:true};
    e._cityBase=e._citySlug==="ashdod"?"../ashdod/":"../rishon-lezion/";
    return e;
  });
  const dbManualKeys=new Set(dbManual.map(e=>e._citySlug+":"+e.event_id));
  const local=localNewEvents().filter(e=>!dbManualKeys.has(e._citySlug+":"+e.event_id)).map(e=>({...e,_localNew:true,_cityBase:e._citySlug==="ashdod"?"../ashdod/":"../rishon-lezion/"}));
  all=[...persisted,...dbManual,...local].map(e=>({...e,_issues:issuesFor(e)}));
  buildFilters();renderSubcategoryFilter();render();
}
function buildFilters(){
  const cities=[...new Set(all.map(e=>e.city).filter(Boolean))].sort();
  $("city").innerHTML='<option value="">כל הערים</option>'+cities.map(x=>'<option>'+esc(x)+'</option>').join("");
  const cats=taxonomyCategories.map(x=>x.id);
  $("category").innerHTML='<option value="">כל הקטגוריות</option>'+cats.map(x=>'<option value="'+esc(x)+'">'+esc(categoryLabels[x]||x)+'</option>').join("");
}
function renderSubcategoryFilter(){
  const cat=taxonomyCategories.find(x=>x.id===$("category").value);
  const items=cat?.subcategories||[];
  $("subcategory").innerHTML='<option value="">כל תתי־הקטגוריות</option>'+items.map(x=>'<option value="'+esc(x.id)+'">'+esc(x.label)+'</option>').join("");
}
function subcategoryLabel(e){
  const cat=taxonomyCategories.find(x=>x.id===e.category);
  return cat?.subcategories?.find(x=>x.id===e.subcategory)?.label||e.subcategory||"—";
}
function filtered(){
  const q=$("q").value.trim().toLowerCase(),city=$("city").value,cat=$("category").value,status=$("status").value,quality=$("quality").value;
  const sub=$("subcategory").value;
  const horizon=horizonEnd();
  return all.filter(e=>{
    if(e.start_date&&e.start_date>horizon)return false;
    if(city&&e.city!==city)return false;
    if(cat&&e.category!==cat)return false;
    if(sub&&e.subcategory!==sub)return false;
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
  const horizon=horizonEnd();
  const active=all.filter(e=>e.start_date>=TODAY&&e.start_date<=horizon);
  const stats=[
    [all.length,"כל האירועים","כולל טיוטות מקומיות"],
    [active.filter(e=>e.status==="active").length,"אירועים עתידיים","פעילים מהיום והלאה"],
    [active.filter(e=>!e._description).length,"חסר תוכן","דורש העשרה"],
    [active.filter(e=>e._issues.some(i=>i.key==="needs_image")).length,"בעיית תמונה","חסרה או לא מאושרת"],
    [active.filter(e=>e._issues.some(i=>i.key==="needs_subcategory")).length,"חסרה תת־קטגוריה","נדרש סיווג לפי תוכן"]
  ];
  $("summary").innerHTML=stats.map(([n,t,s])=>'<article class="stat"><strong>'+n+'</strong><span>'+t+'</span><small>'+s+'</small></article>').join("");
}
function viewsCell(e){
  const id=String(e.event_id||"");
  const v7=Number(analytics.views_7d?.[id]||0);
  const v30=Number(analytics.views_30d?.[id]||0);
  const allTime=Number(analytics.views_all?.[id]||0);
  if(!analytics.generated_at)return '<span class="tag warn" title="ממתין לחיבור GA4">ממתין ל-GA4</span>';
  return '<div class="views-cell" title="7 ימים / 30 ימים / מצטבר"><b>'+allTime.toLocaleString("he-IL")+'</b><small>'+v7.toLocaleString("he-IL")+' / '+v30.toLocaleString("he-IL")+'</small></div>';
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
    const editUrl=(e._localNew?"new.html?v=20261007-1300&edit=1&city=":"edit.html?v=20261007-1300&city=")+encodeURIComponent(e._citySlug)+"&id="+encodeURIComponent(e.event_id);
    const statusLabel=e.status==="draft"?"טיוטה":e.status==="hidden"?"מוסתר":e.status==="archived"?"ארכיון":e.status==="trashed"?"בסל":"";
    const promotionLabel=e.promotion==="promoted"?"מקודם":e.promotion==="recommended"?"מומלץ":"רגיל";
    const promotionClass=e.promotion==="promoted"?"promotion-promoted":e.promotion==="recommended"?"promotion-recommended":"promotion-normal";
    return '<tr>'+
      '<td><div class="event-cell">'+(img?'<img class="thumb" src="'+esc(img)+'" alt="">':'<div class="thumb"></div>')+
      '<div><div class="event-name">'+esc(e.title)+'</div><div class="event-id">'+esc(e.event_id)+'</div>'+(statusLabel?'<span class="status-chip status-'+esc(e.status)+'">'+esc(statusLabel)+'</span>':'')+'</div></div></td>'+
      '<td class="image-status">'+imageStatus+'</td>'+
      '<td>'+esc(e.city)+'</td><td><div class="category-stack"><strong>'+esc(categoryLabels[e.category]||e.category||"—")+'</strong><small>'+esc(subcategoryLabel(e))+'</small></div></td>'+
      '<td>'+esc(fmtDate(e.start_date))+(e.start_time?'<br><small>'+esc(e.start_time)+'</small>':'')+'</td>'+
      '<td>'+esc(e.venue||"—")+'</td><td><div class="issues">'+issues+'</div></td>'+
      '<td><span class="promotion-chip '+promotionClass+'">'+promotionLabel+'</span></td>'+
      '<td class="source" title="'+esc(src)+'">'+esc(src)+'</td>'+
      '<td>'+viewsCell(e)+'</td>'+
      '<td><a class="link" href="'+esc(url)+'" target="_blank" rel="noopener">פתח ↗</a></td>'+
      '<td><a class="edit-link" href="'+esc(editUrl)+'">עריכה ✎</a></td>'+
      '</tr>';
  }).join("");
}
["q","city","status","quality","subcategory"].forEach(id=>$(id).addEventListener("input",render));
$("category").addEventListener("change",()=>{renderSubcategoryFilter();render()});
$("clearBtn").addEventListener("click",()=>{["q","city","category","status","quality","subcategory"].forEach(id=>$(id).value="");renderSubcategoryFilter();render()});
$("refreshBtn").addEventListener("click",load);
load().catch(err=>{$("resultCount").textContent="שגיאה בטעינת הנתונים";console.error(err)});

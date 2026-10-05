const state={events:[],fallbacks:{},generatedAt:null,quick:"all",date:null,category:null,query:"",favoritesOnly:false,sort:"date",discoverSeed:0};
const $=id=>document.getElementById(id);
const fmtDate=new Intl.DateTimeFormat("he-IL",{weekday:"short",day:"numeric",month:"short"});
const fmtFull=new Intl.DateTimeFormat("he-IL",{weekday:"long",day:"numeric",month:"long",year:"numeric"});
const currency=new Intl.NumberFormat("he-IL",{style:"currency",currency:"ILS",maximumFractionDigits:0});
const catLabels={music:"הופעות ומוזיקה",standup:"סטנדאפ",theatre:"תיאטרון והצגות",kids:"ילדים ומשפחה",lecture:"הרצאות וכנסים",exhibition:"תערוכות ואמנות",workshop:"סדנאות ויצירה",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה",sport:"ספורט",tour:"סיורים",other:"עוד"};
const catIcons={music:"♫",standup:"◉",theatre:"◇",kids:"★",lecture:"▣",exhibition:"▤",workshop:"✦",cinema:"▶",festival:"✺",community:"◎",sport:"⚑",tour:"⌖",other:"+"};
const favorites=new Set(JSON.parse(localStorage.getItem("isnet-events-favorites")||"[]"));

function localDate(s){const [y,m,d]=s.split("-").map(Number);return new Date(y,m-1,d)}
function iso(d){return [d.getFullYear(),String(d.getMonth()+1).padStart(2,"0"),String(d.getDate()).padStart(2,"0")].join("-")}
function today(){const d=new Date();d.setHours(0,0,0,0);return d}
function daysFrom(base,n){const d=new Date(base);d.setDate(d.getDate()+n);return d}
function sameDay(a,b){return iso(a)===iso(b)}
function isWeekendDate(d){return d.getDay()===5||d.getDay()===6}
function nextWeekendRange(){
  const t=today(),day=t.getDay();
  let toFri=(5-day+7)%7;
  if(day===6) toFri=6;
  const fri=daysFrom(t,toFri),sat=daysFrom(fri,1);
  return [fri,sat]
}
function formatTime(t){return t||"השעה תפורסם"}
function priceText(e){
  if(e.is_free===true)return "חינם";
  if(e.price_min_ils==null)return "מחיר לא פורסם";
  if(e.price_max_ils!=null&&e.price_max_ils!==e.price_min_ils)return currency.format(e.price_min_ils)+"–"+currency.format(e.price_max_ils);
  return currency.format(e.price_min_ils);
}
function statusBadge(e){
  if(e.ticket_status==="sold_out")return '<span class="badge sold">אזלו הכרטיסים</span>';
  if(e.ticket_status==="last_tickets")return '<span class="badge last">כרטיסים אחרונים</span>';
  if(e.ticket_status==="phone_only")return '<span class="badge">רכישה טלפונית</span>';
  if(e.is_free===true)return '<span class="badge free">חינם</span>';
  return "";
}
function purchaseAction(e){
  if(e.ticket_status==="sold_out")return null;
  const phone=String(e.purchase_phone||"").trim();
  if(phone){
    const dial=phone.replace(/[^0-9+]/g,"");
    if(dial)return {href:"tel:"+dial,label:"חייגו לרכישת כרטיסים",kind:"phone"};
  }
  const url=String(e.purchase_url||"").trim();
  if(/^https?:\/\//i.test(url))return {href:url,label:"לרכישת כרטיסים",kind:"url"};
  return null;
}
function eventGroupKey(e){
  return normalizeSearch(e?.title||"");
}
function eventOccurrences(e){
  if(Array.isArray(e?._occurrences)&&e._occurrences.length)return e._occurrences;
  const key=eventGroupKey(e);
  return state.events
    .filter(x=>eventGroupKey(x)===key)
    .sort((a,b)=>(a.start_date+(a.start_time||"99:99")).localeCompare(b.start_date+(b.start_time||"99:99")));
}
function uniqueOccurrenceDates(e){
  const seen=new Set();
  return eventOccurrences(e).filter(x=>{
    if(seen.has(x.start_date))return false;
    seen.add(x.start_date);return true;
  });
}
function groupedEvent(e,visibleOccurrence=e){
  const occ=eventOccurrences(e);
  if(occ.length<=1)return e;
  const imageEvent=occ.find(x=>hasTrustedSourceImage(x)&&x.thumbnail_ready===true)
    ||occ.find(x=>hasTrustedSourceImage(x))
    ||visibleOccurrence;
  return {
    ...visibleOccurrence,
    image_url:imageEvent.image_url,
    image_origin_url:imageEvent.image_origin_url,
    image_source:imageEvent.image_source,
    image_credit:imageEvent.image_credit,
    image_publishable:imageEvent.image_publishable,
    image_verified:imageEvent.image_verified,
    thumbnail_url:imageEvent.thumbnail_url,
    thumbnail_ready:imageEvent.thumbnail_ready,
    thumbnail_ratio:imageEvent.thumbnail_ratio,
    thumbnail_strategy:imageEvent.thumbnail_strategy,
    _occurrences:occ,
    _group_key:eventGroupKey(e)
  };
}
function groupEvents(arr){
  const grouped=[];
  const seen=new Set();
  for(const e of arr){
    const key=eventGroupKey(e);
    if(seen.has(key))continue;
    seen.add(key);
    grouped.push(groupedEvent(e,e));
  }
  return grouped;
}
function groupFavoriteIds(id){
  const e=state.events.find(x=>x.event_id===id);
  return e?eventOccurrences(e).map(x=>x.event_id):[id];
}
function isGroupFavorite(e){
  return eventOccurrences(e).some(x=>favorites.has(x.event_id));
}
function saveFavorites(){localStorage.setItem("isnet-events-favorites",JSON.stringify([...favorites]))}
function toggleFavorite(id){
  const ids=groupFavoriteIds(id);
  const on=ids.some(x=>favorites.has(x));
  ids.forEach(x=>on?favorites.delete(x):favorites.add(x));
  saveFavorites();render();
}

function hasTrustedSourceImage(e){
  return Boolean(e.image_url&&e.image_publishable===true&&e.image_verified===true);
}
function fallbackImage(e){
  return state.fallbacks?.[e.category]?.image||state.fallbacks?.other?.image||"";
}
function mediaBoxFor(img){
  return img.closest(".featureMedia,.eventMedia,.modal__media");
}
function handleEventImageLoad(img){
  const box=mediaBoxFor(img);
  if(!box)return;
  box.classList.add("has-source-image");
  box.classList.remove("has-fallback-image");
}
function handleEventImageError(img){
  const box=mediaBoxFor(img);
  if(box){
    box.classList.remove("has-source-image");
    box.classList.add("has-fallback-image");
  }
  const stage=img.closest(".eventArtStage");
  if(stage)stage.remove();
  else img.remove();
}
function eventImageHTML(e,mode="card"){
  if(!hasTrustedSourceImage(e))return "";
  const useThumb=mode==="card"&&e.thumbnail_ready===true&&e.thumbnail_url;
  const src=escapeHtml(useThumb?e.thumbnail_url:e.image_url);
  const cls=useThumb?"eventArtMain eventArtThumb":"eventArtMain eventArtFull";
  return '<span class="eventArtStage '+(useThumb?"is-thumbnail":"is-full-image")+'">'+
    '<img data-event-image class="'+cls+'" src="'+src+'" alt="" loading="lazy" onload="handleEventImageLoad(this)" onerror="handleEventImageError(this)">'+
  '</span>';
}
function fallbackMediaHTML(e){
  return '<div class="category-fallback">'+
    '<span class="fallbackMark">'+escapeHtml(catIcons[e.category]||"✦")+'</span>'+
    '<span class="fallbackLabel">'+escapeHtml(catLabels[e.category]||"אירועים")+'</span>'+
  '</div>';
}
function mediaHTML(e,cls="eventMedia"){
  const img=eventImageHTML(e,"card");
  return '<div class="'+cls+' cat-'+e.category+' '+(img?"":"has-fallback-image")+'">'+
    img+fallbackMediaHTML(e)+
    '<button class="heart '+(isGroupFavorite(e)?"is-favorite":"")+'" data-heart="'+e.event_id+'" aria-label="שמירה למועדפים">'+(isGroupFavorite(e)?"♥":"♡")+'</button>'+
  '</div>';
}
function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function dateChipHTML(e){
  const dates=uniqueOccurrenceDates(e);
  if(dates.length<=1){
    const d=localDate(e.start_date);
    return '<div class="dateChip"><b>'+d.getDate()+'</b><span>'+escapeHtml(new Intl.DateTimeFormat("he-IL",{month:"short"}).format(d))+'</span></div>';
  }
  return '<div class="dateStack" aria-label="'+dates.length+' מועדים">'+dates.map(x=>{
    const d=localDate(x.start_date);
    const active=state.date===x.start_date?" is-active":"";
    return '<span class="multiDateChip'+active+'"><b>'+String(d.getDate()).padStart(2,"0")+'</b><span>'+escapeHtml(new Intl.DateTimeFormat("he-IL",{month:"short"}).format(d))+'</span></span>';
  }).join("")+'</div>';
}
function scheduleSummary(e){
  const occ=eventOccurrences(e);
  if(occ.length<=1){
    return fmtFull.format(localDate(e.start_date))+' · '+formatTime(e.start_time);
  }
  const dates=uniqueOccurrenceDates(e);
  const times=[...new Set(occ.map(x=>formatTime(x.start_time)))];
  return occ.length+' מועדים'+(times.length===1?' · '+times[0]:' · שעות שונות');
}
function eventCard(e){
  const occ=eventOccurrences(e);
  const multi=occ.length>1;
  return '<article class="eventCard" data-event="'+e.event_id+'"><div class="mediaWrap">'+mediaHTML(e)+dateChipHTML(e)+'</div>'+
    '<div class="eventBody"><div class="badges"><span class="badge">'+escapeHtml(catLabels[e.category]||"אירוע")+'</span>'+statusBadge(e)+(multi?'<span class="badge datesCount">'+occ.length+' מועדים</span>':'')+'</div>'+
    '<h3>'+escapeHtml(e.title)+'</h3>'+
    '<div class="eventInfo"><span class="eventInfo__row"><i>◷</i><span>'+escapeHtml(scheduleSummary(e))+'</span></span>'+
    '<span class="eventInfo__row"><i>⌖</i><span>'+escapeHtml(e.venue||"המיקום יפורסם")+'</span></span></div>'+
    '<div class="eventFooter"><div class="price">'+escapeHtml(priceText(e))+'</div><span class="linkCue">לפרטים <b>←</b></span></div></div></article>';
}
function featureCard(e){
  return '<article class="featureCard" data-event="'+e.event_id+'">'+mediaHTML(e,"featureMedia")+
    '<div class="featureBody"><div class="badges"><span class="badge">'+escapeHtml(catLabels[e.category]||"אירוע")+'</span>'+statusBadge(e)+'</div>'+
    '<h3>'+escapeHtml(e.title)+'</h3>'+
    '<div class="featureMeta"><span>'+escapeHtml(fmtFull.format(localDate(e.start_date)))+'</span><span>·</span><span>'+escapeHtml(formatTime(e.start_time))+'</span></div>'+
    '<div class="featureVenue">⌖ '+escapeHtml(e.venue||"המיקום יפורסם")+'</div></div></article>';
}

function matchesQuick(e){
  if(state.quick==="all")return true;
  const d=localDate(e.start_date),t=today();
  if(state.quick==="today")return sameDay(d,t);
  if(state.quick==="tomorrow")return sameDay(d,daysFrom(t,1));
  if(state.quick==="weekend"){
    const [fri,sat]=nextWeekendRange();
    return sameDay(d,fri)||sameDay(d,sat);
  }
  if(state.quick==="week")return d>=t&&d<=daysFrom(t,6);
  if(state.quick==="month")return d>=t&&d.getMonth()===t.getMonth()&&d.getFullYear()===t.getFullYear();
  if(state.quick==="kids")return e.category==="kids"||(e.audiences||[]).some(x=>x==="kids"||x==="families");
  if(state.quick==="adults"){
    if((e.audiences||[]).includes("adults")||Number(e.age_min)>=18)return true;
    return ["standup","lecture"].includes(e.category);
  }
  if(state.quick==="free")return e.is_free===true;
  if(state.quick==="standup")return e.category==="standup";
  if(state.quick==="music")return e.category==="music";
  if(state.quick==="lecture")return e.category==="lecture";
  if(state.quick==="theatre")return e.category==="theatre";
  return true
}
function normalizeSearch(s){
  return String(s||"").toLowerCase()
    .replace(/[״"'׳.,!?():;\\/\-–—]/g," ")
    .replace(/\s+/g," ").trim();
}
function editDistance(a,b){
  a=normalizeSearch(a);b=normalizeSearch(b);
  const m=a.length,n=b.length,dp=Array(n+1).fill(0);
  for(let j=0;j<=n;j++)dp[j]=j;
  for(let i=1;i<=m;i++){
    let prev=dp[0];dp[0]=i;
    for(let j=1;j<=n;j++){
      const tmp=dp[j];
      dp[j]=Math.min(dp[j]+1,dp[j-1]+1,prev+(a[i-1]===b[j-1]?0:1));
      prev=tmp;
    }
  }
  return dp[n];
}
function fuzzyTokenMatch(q,hay){
  q=normalizeSearch(q);hay=normalizeSearch(hay);
  if(!q)return true;
  if(hay.includes(q))return true;
  const qTokens=q.split(" ").filter(Boolean),hTokens=hay.split(" ").filter(Boolean);
  return qTokens.every(qt=>hTokens.some(ht=>{
    if(ht.includes(qt)||qt.includes(ht))return true;
    const max=Math.max(qt.length,ht.length);
    if(max<4)return qt===ht;
    return editDistance(qt,ht)<=Math.max(1,Math.floor(max*.28));
  }));
}
function parseSearchIntent(q){
  const s=normalizeSearch(q);
  const intent={category:null,quick:null,free:false,maxPrice:null,terms:[]};
  const categoryAliases=[
    ["kids",["ילדים","ילד","משפחה","משפחתי","הצגת ילדים","פעילות לילדים"]],
    ["standup",["סטנדאפ","סטנד אפ","קומדיה","מצחיק","צחוקים"]],
    ["music",["הופעה","הופעות","מוזיקה","מוסיקה","זמר","זמרת","קונצרט"]],
    ["theatre",["הצגה","הצגות","תיאטרון","מחזה"]],
    ["lecture",["הרצאה","הרצאות","כנס","שיחה"]],
    ["exhibition",["תערוכה","תערוכות","אמנות","מוזיאון"]],
    ["workshop",["סדנה","סדנא","סדנאות","יצירה","קורס"]],
    ["cinema",["סרט","קולנוע","הקרנה"]],
    ["festival",["פסטיבל","יריד","אירוע חוץ"]]
  ];
  for(const [cat,aliases] of categoryAliases){
    if(aliases.some(a=>s.includes(normalizeSearch(a)))){intent.category=cat;break}
  }
  if(/\bהיום\b|הערב/.test(s))intent.quick="today";
  else if(/\bמחר\b/.test(s))intent.quick="tomorrow";
  else if(/סוף השבוע|סופש|שישי|שבת/.test(s))intent.quick="weekend";
  else if(/השבוע/.test(s))intent.quick="week";
  else if(/החודש/.test(s))intent.quick="month";
  if(/חינם|ללא תשלום|כניסה חופשית/.test(s))intent.free=true;
  const pm=s.match(/(?:עד|max|מקסימום)\s*(\d{1,4})\s*(?:שח|שקל|שקלים)?/);
  if(pm)intent.maxPrice=Number(pm[1]);
  const noise=["מה","יש","משהו","אני","רוצה","מחפש","מחפשת","לעשות","בא לי","אירוע","אירועים","היום","הערב","מחר","השבוע","החודש","סוף","השבוע","סופש","שישי","שבת","חינם","ללא","תשלום","כניסה","חופשית","עד","שקל","שקלים"];
  intent.terms=s.split(" ").filter(t=>t&&!noise.includes(t));
  return intent;
}
function eventSearchText(e){
  return [e.title,e.description,e.venue,catLabels[e.category],...(e.audiences||[]),...(e.sources||[]).map(s=>s.name)].filter(Boolean).join(" ");
}
function filtered(){
  const q=state.query.trim();
  const intent=parseSearchIntent(q);
  let arr=state.events.filter(e=>{
    if(!matchesQuick(e))return false;
    if(state.date&&e.start_date!==state.date)return false;
    if(state.category&&e.category!==state.category)return false;
    if(state.favoritesOnly&&!favorites.has(e.event_id))return false;
    if(q){
      if(intent.category&&e.category!==intent.category)return false;
      if(intent.quick){
        const saved=state.quick;state.quick=intent.quick;const ok=matchesQuick(e);state.quick=saved;
        if(!ok)return false;
      }
      if(intent.free&&e.is_free!==true)return false;
      if(intent.maxPrice!=null&&(e.price_min_ils==null||e.price_min_ils>intent.maxPrice))return false;
      const residual=intent.terms.join(" ");
      if(residual&&!fuzzyTokenMatch(residual,eventSearchText(e)))return false;
    }
    return true;
  });
  if(state.sort==="priceLow")arr.sort((a,b)=>(a.price_min_ils??999999)-(b.price_min_ils??999999)||a.start_date.localeCompare(b.start_date));
  else if(state.sort==="priceHigh")arr.sort((a,b)=>(b.price_min_ils??-1)-(a.price_min_ils??-1)||a.start_date.localeCompare(b.start_date));
  else arr.sort((a,b)=>(a.start_date+(a.start_time||"99:99")).localeCompare(b.start_date+(b.start_time||"99:99")));
  return groupEvents(arr)
}

function renderDates(){
  const rail=$("dateRail"),t=today(),counts={};
  state.events.forEach(e=>counts[e.start_date]=(counts[e.start_date]||0)+1);
  rail.innerHTML=Array.from({length:21},(_,i)=>daysFrom(t,i)).map(d=>{
    const id=iso(d),active=state.date===id?" is-active":"",cnt=counts[id]||0;
    return '<button class="dateButton'+active+'" data-date="'+id+'"><small>'+escapeHtml(new Intl.DateTimeFormat("he-IL",{weekday:"short"}).format(d))+'</small><b>'+d.getDate()+'</b><small>'+escapeHtml(new Intl.DateTimeFormat("he-IL",{month:"short"}).format(d))+(cnt?" · "+cnt:"")+'</small></button>';
  }).join("");
}
function renderCategories(){
  const cats=["music","standup","kids","theatre","lecture","exhibition","workshop","cinema","festival"];
  const counts={};groupEvents(state.events).forEach(e=>counts[e.category]=(counts[e.category]||0)+1);
  $("categoryGrid").innerHTML=cats.map(c=>
    '<button class="categoryCard '+(state.category===c?"is-active":"")+'" data-cat="'+c+'">'+
      '<span class="categoryCard__icon">'+catIcons[c]+'</span>'+
      '<span class="categoryCard__copy"><b>'+catLabels[c]+'</b><small>'+((counts[c]||0))+' אירועים</small></span>'+
      '<span class="categoryCard__arrow">←</span>'+
    '</button>').join("");
}
function renderHeroStats(){
  const el=$("heroStats");if(!el)return;
  const upcomingOccurrences=state.events.filter(e=>localDate(e.start_date)>=today());
  const upcoming=groupEvents(upcomingOccurrences);
  const venues=new Set(upcomingOccurrences.map(e=>e.venue).filter(Boolean));
  const categories=new Set(upcomingOccurrences.map(e=>e.category).filter(Boolean));
  let updated="";
  if(state.generatedAt){
    const d=new Date(state.generatedAt);
    if(!Number.isNaN(d.getTime()))updated=new Intl.DateTimeFormat("he-IL",{day:"numeric",month:"numeric",hour:"2-digit",minute:"2-digit"}).format(d);
  }
  el.innerHTML=
    '<span><b>'+upcoming.length+'</b> אירועים קרובים</span>'+
    '<span><b>'+venues.size+'</b> מוקדים בעיר</span>'+
    '<span><b>'+categories.size+'</b> סוגי בילוי</span>'+
    (updated?'<span>עודכן '+escapeHtml(updated)+'</span>':"");
}
function discoverEvents(){
  const upcoming=state.events.filter(e=>localDate(e.start_date)>=today()&&e.ticket_status!=="sold_out");
  const diverse=[],seen=new Set();
  for(const e of upcoming){if(!seen.has(e.category)){diverse.push(e);seen.add(e.category)} if(diverse.length>=6)break}
  const rotated=diverse.slice(state.discoverSeed%Math.max(1,diverse.length)).concat(diverse.slice(0,state.discoverSeed%Math.max(1,diverse.length)));
  return rotated.slice(0,5);
}
function hasActiveSelection(){
  return state.quick!=="all"||Boolean(state.date)||Boolean(state.category)||Boolean(state.query.trim())||state.favoritesOnly||state.sort!=="date";
}
function renderDiscover(){
  const section=$("discoverSection");
  if(hasActiveSelection()){
    section.hidden=true;
    $("discoverGrid").innerHTML="";
    return;
  }
  section.hidden=false;
  const arr=discoverEvents();
  $("discoverGrid").innerHTML=arr.map(featureCard).join("");
}
function renderActiveFilters(){
  const x=[];
  if(state.quick!=="all")x.push({k:"quick",label:$("quickFilters").querySelector('[data-quick="'+state.quick+'"]')?.textContent||state.quick});
  if(state.date)x.push({k:"date",label:fmtFull.format(localDate(state.date))});
  if(state.category)x.push({k:"category",label:catLabels[state.category]||state.category});
  if(state.query)x.push({k:"query",label:'"'+state.query+'"'});
  if(state.favoritesOnly)x.push({k:"favorites",label:"מועדפים"});
  $("activeFilters").innerHTML=x.map(i=>'<button class="filterChip" data-remove="'+i.k+'">'+escapeHtml(i.label)+' ×</button>').join("");
}
function renderResults(){
  const arr=filtered();
  $("eventsGrid").innerHTML=arr.map(eventCard).join("");
  $("resultCount").textContent=arr.length+" אירועים נמצאו";
  $("emptyState").hidden=arr.length>0;
  $("eventsGrid").hidden=arr.length===0;
}
function render(){
  document.querySelectorAll("#quickFilters button").forEach(b=>b.classList.toggle("is-active",b.dataset.quick===state.quick));
  $("favoritesOnly").setAttribute("aria-pressed",state.favoritesOnly?"true":"false");
  renderDates();renderCategories();renderHeroStats();renderActiveFilters();renderResults();
  bindDynamic();
}
function bindDynamic(){
  document.querySelectorAll("[data-event]").forEach(el=>el.onclick=e=>{if(e.target.closest("[data-heart]"))return;openEvent(el.dataset.event)});
  document.querySelectorAll("[data-heart]").forEach(b=>b.onclick=e=>{e.stopPropagation();toggleFavorite(b.dataset.heart)});
  document.querySelectorAll("[data-date]").forEach(b=>b.onclick=()=>{state.date=state.date===b.dataset.date?null:b.dataset.date;state.quick="all";render()});
  document.querySelectorAll("[data-cat]").forEach(b=>b.onclick=()=>{state.category=state.category===b.dataset.cat?null:b.dataset.cat;render()});
  document.querySelectorAll("[data-remove]").forEach(b=>b.onclick=()=>{const k=b.dataset.remove;if(k==="quick")state.quick="all";if(k==="date")state.date=null;if(k==="category")state.category=null;if(k==="query"){state.query="";$("searchInput").value=""}if(k==="favorites")state.favoritesOnly=false;render()});
}
function modalScheduleText(e){
  const occ=eventOccurrences(e);
  return occ.map(x=>fmtFull.format(localDate(x.start_date))+' · '+formatTime(x.start_time)).join(' | ');
}
function groupPurchaseAction(e){
  for(const x of eventOccurrences(e)){
    const action=purchaseAction(x);
    if(action)return action;
  }
  return purchaseAction(e);
}
function openEvent(id){
  const base=state.events.find(x=>x.event_id===id);if(!base)return;
  const e=groupedEvent(base,base);
  const occ=eventOccurrences(e);
  $("modalTitle").textContent=e.title;
  $("modalDescription").textContent=e.description||"כל הפרטים החשובים במקום אחד. מומלץ לוודא את פרטי האירוע מול המארגן לפני הגעה.";
  $("modalBadges").innerHTML='<span class="badge">'+escapeHtml(catLabels[e.category]||"אירוע")+'</span>'+statusBadge(e)+(occ.length>1?'<span class="badge datesCount">'+occ.length+' מועדים</span>':'');
  $("modalMedia").className="modal__media cat-"+(e.category||"other")+(hasTrustedSourceImage(e)?"":" has-fallback-image");
  $("modalMedia").innerHTML=eventImageHTML(e,"modal")+fallbackMediaHTML(e);
  $("modalFacts").innerHTML=[
    [occ.length>1?"מועדים":"תאריך",occ.length>1?modalScheduleText(e):fmtFull.format(localDate(e.start_date))],
    ...(occ.length>1?[]:[["שעה",formatTime(e.start_time)]]),
    ["מקום",e.venue||"יפורסם בהמשך"],
    ["מחיר",priceText(e)]
  ].map(([a,b])=>'<div class="fact"><b>'+a+'</b>'+escapeHtml(b)+'</div>').join("");
  const purchase=groupPurchaseAction(e);
  const link=$("modalTicket");
  const note=$("modalPurchaseNote");
  if(purchase){
    link.href=purchase.href;
    link.textContent=purchase.label;
    link.style.display="inline-flex";
    if(purchase.kind==="phone")link.removeAttribute("target");
    else link.target="_blank";
    note.hidden=true;
    note.textContent="";
  }else{
    link.removeAttribute("href");
    link.style.display="none";
    note.hidden=false;
    note.textContent=occ.every(x=>x.ticket_status==="sold_out")
      ?"הכרטיסים לאירוע אזלו."
      :"אין כרגע קישור רכישה ישיר מאומת. לא נפנה אתכם לעמוד לוח חיצוני; פרטי רכישה ישירים יעודכנו כאן.";
  }
  const fav=$("modalFavorite");fav.dataset.id=id;fav.textContent=(isGroupFavorite(e)?"♥ נשמר במועדפים":"♡ שמירה למועדפים");
  $("eventModal").hidden=false;document.body.style.overflow="hidden";
}
function closeModal(){$("eventModal").hidden=true;document.body.style.overflow=""}
function resetAll(){state.quick="all";state.date=null;state.category=null;state.query="";state.favoritesOnly=false;state.sort="date";$("searchInput").value="";$("sortSelect").value="date";render()}

async function init(){
  const [data,fallbacks]=await Promise.all([fetch("data/events.json?v=20261005-18").then(r=>r.json()),fetch("category-fallbacks.json?v=20261005-18").then(r=>r.json()).catch(()=>({}))]);
  state.events=data.events||[];state.fallbacks=fallbacks;state.generatedAt=data.generated_at||null;render();
  $("searchInput").addEventListener("input",e=>{state.query=e.target.value;render()});
  $("clearSearch").onclick=()=>{state.query="";$("searchInput").value="";render()};
  $("quickFilters").onclick=e=>{const b=e.target.closest("[data-quick]");if(!b)return;state.quick=b.dataset.quick;state.date=null;render()};
  $("resetDate").onclick=()=>{state.date=null;render()};

  $("favoritesOnly").onclick=()=>{state.favoritesOnly=!state.favoritesOnly;render()};
  $("sortSelect").onchange=e=>{state.sort=e.target.value;render()};
  $("resetAll").onclick=resetAll;
  document.querySelectorAll("[data-close-modal]").forEach(x=>x.onclick=closeModal);
  $("modalFavorite").onclick=()=>{toggleFavorite($("modalFavorite").dataset.id);openEvent($("modalFavorite").dataset.id)};
  document.addEventListener("keydown",e=>{if(e.key==="Escape")closeModal()});
}
init().catch(err=>{console.error(err);$("eventsGrid").innerHTML='<div class="emptyState"><h3>לא הצלחנו לטעון את האירועים</h3><p>נסו לרענן את העמוד.</p></div>'});

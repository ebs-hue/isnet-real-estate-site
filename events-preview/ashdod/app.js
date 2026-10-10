// Ashdod GA4: public event metadata only; never transmit raw search text or URLs.
(function () {
  if (!/\/events-preview\/ashdod(?:\/|$)/.test(location.pathname) || window.ashdodAnalytics) return;
  const id = "G-YEFDXMCHB1";
  let debug = new URLSearchParams(location.search).get("ga_debug") === "1";
  try { if (debug) sessionStorage.setItem("ashdod-ga-debug","1"); debug = debug || sessionStorage.getItem("ashdod-ga-debug") === "1"; } catch {}

  const cleanUrl = value => { try { const u = new URL(value); return u.origin + u.pathname; } catch { return ""; } };
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
  if (!window.__ashdodGa4Initialized) {
    window.__ashdodGa4Initialized = true;
    if (!document.querySelector('script[src*="googletagmanager.com/gtag/js"]')) {
      const tag = document.createElement("script");
      tag.async = true; tag.src = "https://www.googletagmanager.com/gtag/js?id=" + id;
      document.head.appendChild(tag);
      window.gtag("js", new Date());
    }
    window.gtag("config", id, {page_location:cleanUrl(location.href), page_referrer:cleanUrl(document.referrer), ...(debug ? {debug_mode:true} : {})});
  }
  const vocabulary = new Set("לאן לצאת מה עושים עם הילדים ילדים ילד ילדה משפחה משפחות היום מחר השבוע סוף שבוע סופש בסופש חינם זול הופעות הופעה מוזיקה מוסיקה סטנדאפ תיאטרון הצגות הצגה קולנוע סרט סרטים הרצאות הרצאה סדנאות סדנה יצירה אמנות אומנות תערוכות תערוכה פסטיבל פסטיבלים קהילה ספורט כדורגל כדורסל כדוריד כדורעף גלישה טיולים טבע פארקים פארק חופים חוף ים אשדוד באשדוד מבוגרים למבוגרים גמלאים גמלאי גיל השלישי אזרחים ותיקים זוג זוגות ערב בוקר צהריים בילוי בילויים לנוער נוער לילדים קטנים קטנות".split(" "));
  const safeSearch = value => {
    const tokens = String(value).normalize("NFKC").toLowerCase().replace(/[^\p{L}\s]/gu," ").split(/\s+/).filter(Boolean);
    // Only recognized generic activity words leave the browser; names, numbers,
    // email addresses and other unknown terms are omitted altogether.
    return [...new Set(tokens.filter(t => vocabulary.has(t)))].join(" ").slice(0,100) || "[withheld]";
  };
  const metadata = e => e ? {event_id:String(e.event_id || "").slice(0,100),event_title:String(e.series_title || e.title || "").slice(0,100),category:String(e.category || "").slice(0,40),event_date:/^\d{4}-\d{2}-\d{2}$/.test(e.start_date || "") ? e.start_date : ""} : {};
  const allowed = new Set(["search","select_category","select_event","select_date","ticket_click"]);
  const send = (name, params = {}) => {
    if (!allowed.has(name)) return;
    window.gtag("event",name,{...params,send_to:id,page_location:cleanUrl(location.href),page_referrer:cleanUrl(document.referrer),transport_type:"beacon",...(debug ? {debug_mode:true} : {})});
  };
  window.ashdodAnalytics = {send,metadata,safeSearch};
})();

const state={events:[],fallbacks:{},generatedAt:null,cinema:[],cinemaVenue:"all",cinemaAudience:"all",cinemaOpen:false,cinemaUpdatedAt:null,sportsMeta:{branches:{},teams:[]},sportTeam:"all",sportBranch:"all",calendarMode:"week",calendarWeek:null,calendarMonth:null,calendarCollapsed:true,periodStart:null,periodEnd:null,periodType:null,quick:"all",date:null,category:null,subcategory:null,query:"",favoritesOnly:false,sort:"date",discoverSeed:0};
const $=id=>document.getElementById(id);
const fmtDate=new Intl.DateTimeFormat("he-IL",{weekday:"short",day:"numeric",month:"short"});
const fmtFull=new Intl.DateTimeFormat("he-IL",{weekday:"long",day:"numeric",month:"long",year:"numeric"});
const currency=new Intl.NumberFormat("he-IL",{style:"currency",currency:"ILS",maximumFractionDigits:0});
const catLabels={music:"הופעות ומוזיקה",standup:"סטנדאפ",theatre:"תיאטרון והצגות",kids:"ילדים ומשפחה",lecture:"הרצאות וכנסים",workshop:"סדנאות ויצירה",exhibition:"תערוכות ואמנות",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה ופנאי",sport:"ספורט באשדוד",seniors:"הגיל השלישי וגמלאים",other:"עוד"};
const catIcons={music:"♫",standup:"◉",theatre:"◇",kids:"★",lecture:"▣",workshop:"✎",exhibition:"▤",cinema:"▶",festival:"✺",community:"◎",sport:"⚑",seniors:"♟",other:"+"};
const favorites=new Set(JSON.parse(localStorage.getItem("isnet-events-favorites")||"[]"));

function localDate(s){const [y,m,d]=s.split("-").map(Number);return new Date(y,m-1,d)}
function iso(d){return [d.getFullYear(),String(d.getMonth()+1).padStart(2,"0"),String(d.getDate()).padStart(2,"0")].join("-")}
function today(){const d=new Date();d.setHours(0,0,0,0);return d}
function daysFrom(base,n){const d=new Date(base);d.setDate(d.getDate()+n);return d}
function startOfWeek(d){const x=new Date(d);x.setHours(0,0,0,0);x.setDate(x.getDate()-x.getDay());return x}
function firstOfMonth(d){const x=new Date(d);x.setHours(0,0,0,0);x.setDate(1);return x}
function addMonths(d,n){const x=new Date(d);x.setDate(1);x.setMonth(x.getMonth()+n);return x}
function sameMonth(a,b){return a.getFullYear()===b.getFullYear()&&a.getMonth()===b.getMonth()}
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
function isNonEventActivity(e){
  const text=[e?.title,e?.series_title,e?.description,e?.variant_label].filter(Boolean).join(" ");
  if(e?.category==="classes")return true;
  return /(?:סדנה|סדנא|סדנת|סדנאות|קורס|קורסים|חוג|חוגים|פילאטיס|יוגה|טאי[־ -]?צ.?י|התעמלות|אימון קבוע|סטודיו פתוח|המרחב הבטוח|שיטת דורון|איזון מפרקים|מפגשים שבועיים|סדרת מפגשים|מחזור לימודים)/i.test(text);
}
function priceText(e){
  if(e.is_free===true)return "חינם";
  if(e.price_min_ils==null)return "מחיר לא פורסם";
  if(e.price_max_ils!=null&&e.price_max_ils!==e.price_min_ils)return currency.format(e.price_min_ils)+"–"+currency.format(e.price_max_ils);
  return currency.format(e.price_min_ils);
}
function sportKey(e){
  const b=String(e?.sport_branch||"");
  if(b.includes("כדורגל"))return "football";
  if(b.includes("כדורסל"))return "basketball";
  if(b.includes("כדוריד"))return "handball";
  if(b.includes("כדורעף"))return "volleyball";
  if(b.includes("גלישה"))return "surfing";
  return "other";
}
function sportBranchMeta(eOrKey){
  const key=typeof eOrKey==="string"?eOrKey:sportKey(eOrKey);
  return state.sportsMeta?.branches?.[key]||{label:"ספורט",icon:"⚑"};
}
function sportTeamConfig(e){
  const home=String(e?.home_team||"").trim();
  const key=sportKey(e);
  return (state.sportsMeta?.teams||[]).find(t=>
    (t.match_home_teams||[]).includes(home)&&(!(t.sports||[]).length||(t.sports||[]).includes(key))
  )||null;
}
function teamInitials(name){
  return String(name||"קבוצה").split(/\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join("");
}
function teamLogoHTML(team,cls="teamLogo"){
  const name=team?.name||"קבוצה";
  const img=team?.logo_url
    ?'<img src="'+escapeHtml(team.logo_url)+'" alt="" loading="lazy" onerror="this.remove()">'
    :"";
  return '<span class="'+cls+'" aria-hidden="true"><b>'+escapeHtml(teamInitials(name))+'</b>'+img+'</span>';
}
function isRepresentativeHomeGame(e){
  return e?.category==="sport"&&e?.is_home_game===true&&e?.representative_team===true&&Boolean(e?.home_team);
}
function sportIdentityHTML(e){
  if(!isRepresentativeHomeGame(e))return "";
  const team=sportTeamConfig(e);
  const branch=sportBranchMeta(e);
  const name=team?.name||e.home_team||e.organizer||"קבוצה אשדודית";
  return '<div class="sportIdentity">'+
    teamLogoHTML(team,"sportIdentity__logo")+
    '<div class="sportIdentity__copy"><b>'+escapeHtml(name)+'</b><small><span class="sportGlyph">'+escapeHtml(branch.icon)+'</span>'+escapeHtml(branch.label)+' · משחק בית</small></div>'+
  '</div>';
}
function sportBranchBadgeHTML(e){
  if(e.category!=="sport")return "";
  const branch=sportBranchMeta(e);
  return '<span class="badge sportBranchBadge">'+escapeHtml(branch.icon)+' '+escapeHtml(branch.label)+'</span>';
}
function statusBadge(e){
  if(e.ticket_status==="sold_out")return '<span class="badge sold">אזלו הכרטיסים</span>';
  if(e.ticket_status==="last_tickets")return '<span class="badge last">כרטיסים אחרונים</span>';
  if(e.ticket_status==="phone_only")return '<span class="badge">רכישה טלפונית</span>';
  if(e.is_free===true)return '<span class="badge free">חינם</span>';
  return "";
}
function isBlockedPurchaseUrl(url){
  try{
    const host=new URL(url,location.href).hostname.toLowerCase();
    return host==="live.tickchak.co.il"||host==="tickchak.co.il"||host.endsWith(".tickchak.co.il");
  }catch{return true}
}
function purchaseAction(e){
  if(e.ticket_status==="sold_out")return null;
  const phone=String(e.purchase_phone||"").trim();
  if(phone){
    const dial=phone.replace(/[^0-9+]/g,"");
    if(dial)return {href:"tel:"+dial,label:"חייגו לרכישת כרטיסים",kind:"phone"};
  }
  const url=String(e.purchase_url||"").trim();
  if(/^https?:\/\//i.test(url)&&!isBlockedPurchaseUrl(url))return {href:url,label:"לרכישת כרטיסים",kind:"url"};
  return null;
}
function eventGroupKey(e){
  if(e?.series_id)return "series:"+String(e.series_id);
  if(isRepresentativeHomeGame(e)){
    const team=sportTeamConfig(e);
    const teamKey=team?.id||normalizeSearch(e.home_team||e.organizer||"sport-team");
    const branchKey=normalizeSearch(e.sport_branch||sportBranchMeta(e).label||sportKey(e));
    return "sport-team:"+teamKey+":"+branchKey;
  }
  return normalizeSearch(e?.title||"");
}
function eventDisplayTitle(e){
  return e?.series_title||e?.title||"אירוע";
}
function eventOccurrences(e){
  if(Array.isArray(e?._occurrences)&&e._occurrences.length)return e._occurrences;
  const key=eventGroupKey(e);
  return state.events
    .filter(x=>eventGroupKey(x)===key)
    .sort((a,b)=>(a.start_date+(a.start_time||"99:99")).localeCompare(b.start_date+(b.start_time||"99:99")));
}
function isPersistentExhibition(e){
  if(e?.category!=="exhibition")return false;
  if(e.end_date){
    const a=localDate(e.start_date),b=localDate(e.end_date);
    if(!Number.isNaN(a.getTime())&&!Number.isNaN(b.getTime())&&((b-a)/86400000)>=7)return true;
  }
  const dates=[...new Set(eventOccurrences(e).map(x=>x.start_date).filter(Boolean))];
  return dates.length>=4;
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
  if(occ.length<=1)return e.series_title?{...e,title:eventDisplayTitle(e),description:e.series_description||e.description}:e;
  const imageEvent=occ.find(x=>hasTrustedSourceImage(x)&&x.thumbnail_ready===true)
    ||occ.find(x=>hasTrustedSourceImage(x))
    ||visibleOccurrence;
  const isSportGroup=isRepresentativeHomeGame(visibleOccurrence);
  const sportTeam=isSportGroup?sportTeamConfig(visibleOccurrence):null;
  const sportName=sportTeam?.name||visibleOccurrence.home_team||visibleOccurrence.organizer||"הקבוצה";
  return {
    ...visibleOccurrence,
    title:isSportGroup?"משחקי הבית הקרובים":eventDisplayTitle(visibleOccurrence),
    description:isSportGroup?occ.length+" משחקי הבית הקרובים של "+sportName:(visibleOccurrence.series_description||visibleOccurrence.description),
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
const SPECIAL_EVENT_ART={
  "הרצאה של יונתן סררו":"assets/special/y-serror-lecture.svg",
  "סערה בדלי מים":"assets/special/storm-in-glass.svg",
  "תשאירי פתוח":"assets/special/leave-open.svg",
  "שירי קריוקי בקצב הדרבוקה":"assets/special/karaoke-darbuka.svg"
};
function specialEventArt(e){return SPECIAL_EVENT_ART[String(e?.title||"").trim()]||""}

function eventImageHTML(e,mode="card"){
  const special=specialEventArt(e);
  if(!special&&!hasTrustedSourceImage(e))return "";
  const useThumb=!special&&mode==="card"&&e.thumbnail_ready===true&&e.thumbnail_url;
  const src=escapeHtml(special||(useThumb?e.thumbnail_url:e.image_url));
  const cls=useThumb?"eventArtMain eventArtThumb":"eventArtMain eventArtFull";
  return '<span class="eventArtStage '+(useThumb?"is-thumbnail":"is-full-image")+'">'+
    '<img data-event-image class="'+cls+'" src="'+src+'" alt="" loading="lazy" onload="handleEventImageLoad(this)" onerror="handleEventImageError(this)">'+
  '</span>';
}

const LECTURE_FALLBACK_TOPICS=[
 {label:"היסטוריה ומורשת",symbol:"⌛",words:/היסטור|תנך|תנ״ך|ארץ ישראל|ישראל|מורשת|מלחמ|אקטואל|רבינ|בגין|עבר/},
 {label:"תרבות, ספרות ואמנות",symbol:"✺",words:/אמנות|אומנות|ציור|ספרו|ספר|קולנוע|מוזיק|יציר|תרבות|שירה|אמנ/},
 {label:"מדע ומחשבה",symbol:"◇",words:/מדע|מוח|טכנולוג|חלל|בינה|מחשב|פיזיק|חקר|פילוסופ|פסיכולוג/},
 {label:"בריאות ואורח חיים",symbol:"✧",words:/בריא|גוף|נפש|תזונה|יוגה|רפואה|הזדקנו|זיכרון|מיינדפולנס/},
 {label:"משפחה וחברה",symbol:"♡",words:/משפח|הורו|יחסי|זוגי|קהיל|ילד|חינוך|חבר|התבגרו/},
 {label:"הרצאות והעשרה",symbol:"✦",words:/$^/}
];
function lectureFallbackTopic(e){
 const text=String(e.title||"");
 const found=LECTURE_FALLBACK_TOPICS.find(x=>x.words.test(text));
 if(found)return found;
 const textId=String(e.event_id||e.title||"");
 const hash=[...textId].reduce((n,c)=>(n*31+c.charCodeAt(0))>>>0,7);
 const extras=[...LECTURE_FALLBACK_TOPICS];
 return {label:"הרצאות והעשרה",symbol:extras[hash%extras.length].symbol};
}
const DEFAULT_IMAGE_CATEGORIES=new Set(["music","theatre","standup","kids","lecture","conference","exhibition","festival","community","tour","sport","cinema","food","seniors"]);
function defaultCategoryImage(e){
  const raw=String(e?.category||"");
  const cat=DEFAULT_IMAGE_CATEGORIES.has(raw)?raw:(raw==="workshop"?"exhibition":"community");
  const sub=String(e?.subcategory||"").replace(/[^a-z0-9-]/g,"");
  return {primary:"../shared/images/defaults/category-"+cat+".svg",subcategory:sub&&cat===raw?"../shared/images/defaults/"+cat+"-"+sub+".svg":""};
}
function defaultCategoryArt(e){
  const paths=defaultCategoryImage(e);
  const src=paths.subcategory||paths.primary;
  return '<img class="defaultCategoryArt" src="'+escapeHtml(src)+'" alt="" loading="lazy" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.82;pointer-events:none" data-primary-fallback="'+escapeHtml(paths.primary)+'" onerror="if(this.dataset.primaryFallback && !this.dataset.triedPrimary){this.dataset.triedPrimary=\'1\';this.src=this.dataset.primaryFallback}else{this.remove()}" />';
}
function fallbackMediaHTML(e){
  if(e.category==="sport"&&isRepresentativeHomeGame(e)){
    const team=sportTeamConfig(e),branch=sportBranchMeta(e);
    return '<div class="category-fallback sportFallback">'+
      defaultCategoryArt(e)+teamLogoHTML(team,"sportFallback__logo")+
      '<span class="sportFallback__branch">'+escapeHtml(branch.icon)+' '+escapeHtml(branch.label)+'</span>'+
      '<span class="fallbackLabel">'+escapeHtml(team?.name||e.home_team||"ספורט באשדוד")+'</span>'+
    '</div>';
  }
  if(e.category==="lecture"){
    const topic=lectureFallbackTopic(e);
    return '<div class="category-fallback lectureArtwork" aria-label="איור להמחשה: '+escapeHtml(topic.label)+'">'+
      defaultCategoryArt(e)+'<span class="fallbackMark">'+escapeHtml(topic.symbol)+'</span>'+
      '<span class="fallbackLabel">'+escapeHtml(topic.label)+'</span></div>';
  }
  return '<div class="category-fallback">'+
    defaultCategoryArt(e)+'<span class="fallbackMark">'+escapeHtml(catIcons[e.category]||"✦")+'</span>'+
    '<span class="fallbackLabel">'+escapeHtml(catLabels[e.category]||"אירועים")+'</span>'+
  '</div>';
}
function eventVideoInfo(e){
  if(!["theatre","standup"].includes(e.category))return null;
  const occurrence=(eventOccurrences(e)||[]).find(x=>/^[A-Za-z0-9_-]{11}$/.test(String(x.youtube_id||"")));
  const item=occurrence||e;
  const id=String(item.youtube_id||"");
  return /^[A-Za-z0-9_-]{11}$/.test(id)?{id,title:item.youtube_title||"צפו בקטע מהמופע"}:null;
}
function eventVideoButton(e){
  const video=eventVideoInfo(e);
  if(!video)return "";
  return '<button type="button" class="eventVideoButton" data-event-video="'+escapeHtml(e.event_id)+'" aria-label="צפו בסרטון מהאירוע '+escapeHtml(e.title)+'"><span aria-hidden="true">▶</span> צפו בסרטון</button>';
}
function mediaHTML(e,cls="eventMedia"){
  const img=eventImageHTML(e,"card");
  return '<div class="'+cls+' cat-'+e.category+' '+(img?"":"has-fallback-image")+'">'+
    img+fallbackMediaHTML(e)+
    '<button class="heart '+(isGroupFavorite(e)?"is-favorite":"")+'" data-heart="'+e.event_id+'" aria-label="שמירה למועדפים">'+(isGroupFavorite(e)?"♥":"♡")+'</button>'+eventVideoButton(e)+
  '</div>';
}
function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function dateChipHTML(e){
  const dates=uniqueOccurrenceDates(e);
  if(dates.length<=1){
    const d=localDate(e.start_date);
    return '<div class="dateChip"><b>'+d.getDate()+'</b><span>'+escapeHtml(new Intl.DateTimeFormat("he-IL",{month:"short"}).format(d))+'</span></div>';
  }
  // The card previews five different dates on desktop and four on mobile.
  // The full schedule still lives on the event page; never truncate stored dates.
  const chips=dates.slice(0,5).map(x=>{
    const d=localDate(x.start_date);
    const active=state.date===x.start_date?" is-active":"";
    return '<span class="multiDateChip'+active+'"><b>'+String(d.getDate()).padStart(2,"0")+'</b><span>'+escapeHtml(new Intl.DateTimeFormat("he-IL",{month:"short"}).format(d))+'</span></span>';
  }).join("");
  const href="event.html?id="+encodeURIComponent(e.event_id)+"#dates";
  const more=limit=>{
    const remaining=dates.length-limit;
    return remaining>0
      ?'<a class="dateStack__more dateStack__more--'+(limit===4?"mobile":"desktop")+
        '" href="'+escapeHtml(href)+'" aria-label="לצפייה בכל המועדים, '+(remaining===1?"עוד מועד אחד":"עוד "+remaining+" מועדים")+'">'+(remaining===1?"עוד מועד אחד":"עוד "+remaining+" מועדים")+' <span aria-hidden="true">←</span></a>'
      :"";
  };
  return '<div class="dateStack" aria-label="'+dates.length+' תאריכים שונים">'+chips+more(5)+more(4)+'</div>';
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
  return '<article class="eventCard'+(e.category==="sport"?" eventCard--sport":"")+'" data-event="'+e.event_id+'"><div class="mediaWrap">'+mediaHTML(e)+dateChipHTML(e)+'</div>'+
    '<div class="eventBody">'+sportIdentityHTML(e)+'<div class="badges"><button type="button" class="badge categoryBadge" data-cat="'+escapeHtml(e.category||"other")+'" title="הצג עוד אירועים בקטגוריה">'+escapeHtml(catLabels[e.category]||"אירוע")+' ←</button>'+sportBranchBadgeHTML(e)+statusBadge(e)+(multi?'<span class="badge datesCount">'+occ.length+' מועדים</span>':'')+'</div>'+
    '<h3>'+escapeHtml(e.title)+'</h3>'+
    '<div class="eventInfo"><span class="eventInfo__row"><i>◷</i><span>'+escapeHtml(scheduleSummary(e))+'</span></span>'+
    '<span class="eventInfo__row"><i>⌖</i><span>'+escapeHtml(e.venue||"המיקום יפורסם")+'</span></span></div>'+
    '<div class="eventFooter"><div class="price">'+escapeHtml(priceText(e))+'</div><span class="linkCue">לפרטים <b>←</b></span></div></div></article>';
}
function featureCard(e){
  return '<article class="featureCard" data-event="'+e.event_id+'">'+mediaHTML(e,"featureMedia")+
    '<div class="featureBody">'+sportIdentityHTML(e)+'<div class="badges"><button type="button" class="badge categoryBadge" data-cat="'+escapeHtml(e.category||"other")+'" title="הצג עוד אירועים בקטגוריה">'+escapeHtml(catLabels[e.category]||"אירוע")+' ←</button>'+statusBadge(e)+'</div>'+
    '<h3>'+escapeHtml(e.title)+'</h3>'+
    '<div class="featureMeta"><span>'+escapeHtml(fmtFull.format(localDate(e.start_date)))+'</span><span>·</span><span>'+escapeHtml(formatTime(e.start_time))+'</span></div>'+
    '<div class="featureVenue">⌖ '+escapeHtml(e.venue||"המיקום יפורסם")+'</div></div></article>';
}

function cinemaScheduleInfo(venue){
  const day=iso(today());
  const schedule=venue.schedule||{};
  if(Array.isArray(schedule[day])&&schedule[day].length){
    return {date:day,label:"היום",times:schedule[day]};
  }
  const next=Object.keys(schedule).filter(d=>d>=day).sort()[0];
  if(next){
    const d=localDate(next);
    const label=sameDay(d,daysFrom(today(),1))?"מחר":new Intl.DateTimeFormat("he-IL",{weekday:"short",day:"numeric",month:"short"}).format(d);
    return {date:next,label,times:schedule[next]};
  }
  return {date:null,label:"לשעות מעודכנות",times:[]};
}
function cinemaCard(movie){
  const visibleVenues=movie.venues.filter(v=>state.cinemaVenue==="all"||v.id===state.cinemaVenue);
  const hasTrailer=Boolean(movie.trailer_youtube_id);
  const image=hasTrailer?"https://i.ytimg.com/vi/"+encodeURIComponent(movie.trailer_youtube_id)+"/hqdefault.jpg":"";
  const venues=visibleVenues.map(v=>{
    const info=cinemaScheduleInfo(v);
    const times=info.times.length?info.times.slice(0,6).map(t=>'<span class="cinemaTime">'+escapeHtml(t)+'</span>').join(""):'<span class="cinemaNoTimes">בדקו שעות עדכניות</span>';
    return '<div class="cinemaVenueRow">'+
      '<div class="cinemaVenueName"><b>'+escapeHtml(v.name)+'</b><span>'+escapeHtml(info.label)+'</span></div>'+
      '<div class="cinemaTimes">'+times+'</div>'+
      '<a href="movie.html?id='+encodeURIComponent(movie.id)+'" class="cinemaDetails">כל הימים והשעות ←</a>'+
    '</div>';
  }).join("");
  const media=hasTrailer
    ?'<button class="cinemaPoster" data-trailer="'+escapeHtml(movie.id)+'" aria-label="צפו בטריילר של '+escapeHtml(movie.title)+'">'+
       '<img src="'+image+'" alt="" loading="lazy">'+
       '<span class="cinemaPlay"><i>▶</i><b>צפו בטריילר</b></span>'+
     '</button>'
    :'<div class="cinemaPoster cinemaPoster--fallback"><span class="cinemaFallbackIcon">🎬</span><b>'+escapeHtml(movie.title)+'</b><span>לשעות ופרטים בעמוד הסרט</span></div>';
  return '<article class="cinemaCard" data-movie="'+escapeHtml(movie.id)+'">'+
    media+
    '<div class="cinemaCard__body">'+
      '<div class="cinemaVenueBadges">'+
        (movie.is_family?'<span class="family">ילדים ומשפחה</span>':'')+
        visibleVenues.map(v=>'<span>'+escapeHtml(v.id==="cinema-city"?"סינמה סיטי":"HOT Cinema")+'</span>').join("")+
      '</div>'+
      '<h3>'+escapeHtml(movie.title)+'</h3>'+
      '<p>'+escapeHtml(movie.synopsis||"")+'</p>'+
      '<div class="cinemaSchedules">'+venues+'</div>'+
    '</div>'+
  '</article>';
}
function renderCinema(){
  const grid=$("cinemaGrid"),section=$("cinemaSection"); if(!grid||!section)return;
  section.hidden=!state.cinemaOpen;
  if(!state.cinemaOpen){grid.innerHTML="";return}
  const arr=state.cinema
    .filter(m=>state.cinemaAudience==="all"||m.is_family===true)
    .filter(m=>state.cinemaVenue==="all"||m.venues.some(v=>v.id===state.cinemaVenue))
    .sort((a,b)=>{
      const day=iso(today());
      const at=a.venues.some(v=>Array.isArray(v.schedule?.[day])&&v.schedule[day].length)?0:1;
      const bt=b.venues.some(v=>Array.isArray(v.schedule?.[day])&&v.schedule[day].length)?0:1;
      return at-bt||a.title.localeCompare(b.title,"he");
    });
  grid.innerHTML=arr.length?arr.map(cinemaCard).join(""):'<div class="cinemaEmpty"><h3>סרטי הקולנוע בעיר מתעדכנים</h3><p>עדיין אין במאגר סרטים מאומתים עם שעות הקרנה לבית הקולנוע שבחרתם. לא נציג שעות או טריילרים לא בדוקים.</p><p>ניתן בינתיים לבדוק את ההקרנות באתרים הרשמיים של בתי הקולנוע.</p><div class="cinemaEmpty__links"><a href="https://www.cinema-city.co.il/" target="_blank" rel="noopener noreferrer">סינמה סיטי ←</a><a href="https://www.planetcinema.co.il/rishon" target="_blank" rel="noopener noreferrer">פלאנט ראשון לציון ←</a></div></div>';
  document.querySelectorAll("#cinemaFilters [data-cinema]").forEach(b=>b.classList.toggle("is-active",b.dataset.cinema===state.cinemaVenue));
  document.querySelectorAll("#cinemaAudienceFilters [data-audience]").forEach(b=>b.classList.toggle("is-active",b.dataset.audience===state.cinemaAudience));
  document.querySelectorAll("[data-trailer]").forEach(b=>b.onclick=e=>{e.stopPropagation();openTrailer(b.dataset.trailer)});
  document.querySelectorAll("[data-movie]").forEach(card=>card.onclick=e=>{
    if(e.target.closest("[data-trailer],a,button"))return;
    location.href="movie.html?id="+encodeURIComponent(card.dataset.movie);
  });
  const updated=$("cinemaUpdated");
  if(updated){
    let suffix=arr.length+" סרטים";
    if(state.cinemaAudience==="family")suffix=arr.length+" סרטים לילדים ולמשפחה";
    if(state.cinemaUpdatedAt){
      const d=new Date(state.cinemaUpdatedAt);
      const stamp=Number.isNaN(d.getTime())?"":" · עודכן "+new Intl.DateTimeFormat("he-IL",{day:"numeric",month:"numeric",hour:"2-digit",minute:"2-digit"}).format(d);
      updated.textContent=suffix+stamp;
    }else updated.textContent=suffix;
  }
}
function openTrailer(id){
  const movie=state.cinema.find(m=>m.id===id); if(!movie||!movie.trailer_youtube_id)return;
  $("trailerTitle").textContent=movie.title;
  $("trailerSynopsis").textContent=movie.synopsis||"";
  $("trailerFrame").src="https://www.youtube-nocookie.com/embed/"+encodeURIComponent(movie.trailer_youtube_id)+"?autoplay=1&rel=0";
  $("trailerFrame").title="טריילר - "+movie.title;
  $("trailerLinks").innerHTML='<a href="movie.html?id='+encodeURIComponent(movie.id)+'">כל הימים, השעות והפרטים אצלנו ←</a>';
  $("trailerModal").hidden=false;
  document.body.style.overflow="hidden";
}
function openEventVideo(eventId){
  const e=state.events.find(item=>String(item.event_id)===String(eventId));
  if(!e)return;
  const video=eventVideoInfo(e);
  if(!video)return;
  $("trailerTitle").textContent=e.series_title||e.title||"סרטון מהאירוע";
  $("trailerSynopsis").textContent=video.title;
  $("trailerFrame").src="https://www.youtube-nocookie.com/embed/"+video.id+"?autoplay=1&rel=0";
  $("trailerFrame").title=video.title;
  $("trailerLinks").innerHTML='<a href="event.html?id='+encodeURIComponent(e.event_id)+'">כל פרטי האירוע והמועדים אצלנו ←</a>';
  $("trailerModal").hidden=false;
  document.body.style.overflow="hidden";
}
function closeTrailer(){
  const modal=$("trailerModal"); if(!modal)return;
  modal.hidden=true;
  $("trailerFrame").src="";
  if($("eventModal").hidden)document.body.style.overflow="";
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
/* Hebrew intent search: local, explainable relevance ranking without an external AI API. */
const SEARCH_CONCEPTS=[
  {id:"family",words:["ילד","ילדים","ילדות","ילדה","קטנטנים","פעוט","פעוטות","משפחה","משפחות","הורים","בייבי","נוער","בן שלי","בת שלי","לילדים","עם הילד"],cats:{kids:15,festival:6,exhibition:4,theatre:3},eventWords:["ילדים","ילד","משפחה","ילדות","תינוק","הצגת ילדים","שעת סיפור"],label:"ילדים ומשפחה"},
  {id:"funny",words:["צחוק","לצחוק","מצחיק","מצחיקה","מצחיקים","קומדיה","הומור","סטנדאפ","סטנד אפ","בידור","משעשע"],cats:{standup:18,theatre:7,kids:3},eventWords:["סטנדאפ","קומדיה","מצחיק","בידור"],label:"משהו מצחיק"},
  {id:"music",words:["מוזיקה","מוסיקה","מופע","מופעים","הופעה","הופעות","זמר","זמרת","קונצרט","שירים","שירה","לייב"],cats:{music:16,festival:4},eventWords:["הופעה","מוזיקה","מוסיקה","קונצרט","זמר","שירה"],label:"הופעות ומוזיקה"},
  {id:"theatre",words:["הצגה","הצגות","תיאטרון","מחזה","מחזמר","במה"],cats:{theatre:16,kids:7},eventWords:["הצגה","מחזמר","תיאטרון"],label:"הצגות"},
  {id:"learn",words:["הרצאה","הרצאות","ללמוד","לימוד","להעשיר","ידע","העשרה","כנס","שיחה","מרצה"],cats:{lecture:15,exhibition:5},eventWords:["הרצאה","סדנה","כנס","מפגש"],label:"הרצאות והעשרה"},
  {id:"create",words:["סדנה","סדנאות","סדנא","יצירה","יצירתי","לעשות משהו","פעילות","פעילויות","התנסות","ציור","אמנות מעשית"],cats:{kids:7,exhibition:4},eventWords:["סדנה","יצירה","מפגש","קורס"],label:"סדנאות ופעילויות"},
  {id:"culture",words:["תרבות","מוזיאון","אמנות","אומנות","תערוכה","תערוכות","גלריה","היסטוריה"],cats:{exhibition:17,theatre:7,lecture:7,music:4},eventWords:["מוזיאון","תערוכה","אמנות","גלריה"],label:"תרבות ואמנות"},
  {id:"sports",words:["ספורט","משחק","משחקים","כדורגל","כדורסל","כדוריד","כדורעף","קבוצה","קבוצות","אצטדיון"],cats:{sport:18},eventWords:["מכבי","הפועל","כדורגל","כדורסל","משחק"],label:"ספורט"},
  {id:"outdoors",words:["בחוץ","באוויר הפתוח","בטבע","טבע","טיול","טיולים","פארק","ים","חוף","הליכה","בחיק הטבע","אטרקציות"],cats:{sport:4,festival:9,community:4,kids:2},eventWords:["חוף","ים","טיול","פארק","גלישה","שטח","אוויר הפתוח"],label:"בילוי בחוץ"},
  {id:"dateNight",words:["זוג","זוגי","זוגית","זוגיות","דייט","רומנטי","רומנטית","בני זוג","ערב זוגי","בילוי זוגי"],cats:{music:9,standup:9,theatre:9},eventWords:["אהבה","זוג","רומנטי"],label:"בילוי זוגי"},
  {id:"relax",words:["רגוע","רגועה","שקט","שקטה","נינוח","נינוחה","קליל","קלילה","לא רועש"],cats:{exhibition:9,lecture:7,music:4},eventWords:["מוזיאון","גלריה","קריאה","הרצאה"],label:"בילוי רגוע"},
  {id:"seniors",words:["מבוגרים","מבוגר","בוגרים","גיל השלישי","גמלאים","פנסיונרים","ותיקים","ותיקות"],cats:{lecture:8,music:7,theatre:7,exhibition:7},eventWords:["גיל השלישי","ותיקים","60"],label:"למבוגרים"}
];
const SEARCH_STOPWORDS=new Set(["מה","יש","לי","לנו","עם","אני","אנחנו","רוצה","רוצים","רוצות","מחפש","מחפשת","מחפשים","תמצא","תמצאי","תן","תני","אפשר","בא","בא לי","לעשות","לצאת","לבלות","משהו","איזה","איזו","איפה","מתי","אשדוד","באשדוד","בעיר","קרוב","לי","לנו","הכי","של","על","את","או","ו","ב","ל","בבקשה","מתאים","שיתאים","מעניין","נחמד","כיף","כיפי","כיפית","טוב","טובה","היום","מחר","השבוע","החודש","שבת","שישי","בערב","ערב","הלילה","סופש","סוף","השבוע","ללא","תשלום","חינם","עד","שח","שקל","שקלים","ילד","ילדים","משפחה","משפחות","הופעה","הופעות","הצגה","הצגות","קולנוע","סרט","סרטים","בת","בן","גיל"]);
function hebrewSearchText(s){
  return normalizeSearch(s).replace(/[\u0591-\u05C7]/g,"").replace(/(?:ם)(?=\s|$)/g,"מ").replace(/(?:ן)(?=\s|$)/g,"נ");
}
function searchWordForms(w){
  const x=hebrewSearchText(w);
  const forms=new Set([x]);
  if(x.length>=5&&/^[ובלכהמש]/.test(x))forms.add(x.slice(1));
  if(x.length>=6&&/^(ליל|למש|במש)/.test(x))forms.add(x.slice(1));
  return [...forms];
}
function textIncludesConcept(text,words){
  const normalized=hebrewSearchText(text);
  const tokens=normalized.split(" ");
  return words.some(w=>{
    const phrase=hebrewSearchText(w);
    if(phrase.includes(" "))return normalized.includes(phrase);
    return tokens.some(t=>searchWordForms(t).some(f=>f===phrase||(phrase.length>=4&&f.startsWith(phrase))||(f.length>=4&&phrase.startsWith(f))));
  });
}
function intentSearchDate(q){
  const s=normalizeSearch(q);
  if(/מחר/.test(s))return "tomorrow";
  if(/היום|הערב|הלילה/.test(s))return "today";
  if(/סוף השבוע|סופש|בשבת|ביום שבת|יום שבת|בשישי|יום שישי/.test(s))return "weekend";
  if(/השבוע/.test(s))return "week";
  if(/החודש/.test(s))return "month";
  return null;
}
function parseSearchIntent(q){
  const s=normalizeSearch(q),concepts=SEARCH_CONCEPTS.filter(c=>textIncludesConcept(s,c.words));
  const date=intentSearchDate(s);
  const free=/חינם|ללא תשלום|בלי לשלם|לא עולה כסף/.test(s);
  const pm=s.match(/(?:עד|מקסימום|תקציב)\s*(\d{1,4})\s*(?:שח|שקל|שקלים)?/);
  const maxPrice=pm?Number(pm[1]):null;
  const ageMatch=s.match(/(?:בן|בת|גילאי?|גיל)\s*(\d{1,2})/);
  const age=ageMatch?Number(ageMatch[1]):null;
  // Remove conversational instructions, prepositions and recognized concepts.
  // Only specific names/venues remain as required keyword signals.
  const conversational=new Set(["לאן","לאיפה","לאיזה","לאיזו","היכן","איפה","כיצד","איך","אפשרי","רעיונות","רעיון","המלצות","המלצה","הצעות","תציע","תציעו","להציע","תן","תני","תנו","תרצה","תמצאו","לצאת","לצאתם","ללכת","לבלות","בוא","בואו","כדאי","מומלץ","מומלצת","כייפי","כיפי","הילדים","הילדות","הקטנים","הקטנות","המשפחה","משפחתית","לילדים","למשפחה","והילדים","באשדוד","באזור","בסביבה","בסביבה שלי","הלילה","בערב","לערב","לשבת","בשבת","בסופש","במחר","להיום","השבת","בחינם","זול","זולה","מחיר","תקציב","מקסימום","בילוי","פעילות","פעילויות","אירוע","אירועים","דברים","אטרקציה","אטרקציות","מקומות","מקום","הצגה","הצגות","הופעה","הופעות","מופע","מופעים"]);
  const remaining=s.split(/\s+/).filter(w=>
    w&&!SEARCH_STOPWORDS.has(w)&&!conversational.has(w)&&
    !concepts.some(c=>textIncludesConcept(w,c.words))&&
    !/^\d+$/.test(w)
  );
  return {concepts,date,free,maxPrice,age,terms:remaining,query:s};
}
function eventSearchText(e){
  return [e.title,e.description,e.venue,e.organizer,e.home_team,e.away_team,e.sport_branch,catLabels[e.category],...(e.audiences||[]),...(e.sources||[]).map(s=>s.name)].filter(Boolean).join(" ");
}
function searchDateMatches(e,period){
  if(!period)return true;
  const d=localDate(e.start_date),t=today();
  if(period==="today")return sameDay(d,t);
  if(period==="tomorrow")return sameDay(d,daysFrom(t,1));
  if(period==="weekend"){const [fri,sat]=nextWeekendRange();return sameDay(d,fri)||sameDay(d,sat)}
  if(period==="week")return d>=t&&d<=daysFrom(t,6);
  if(period==="month")return d>=t&&sameMonth(d,t);
  return true;
}
function eventSemanticScore(e,intent){
  if(intent.date&&!searchDateMatches(e,intent.date))return null;
  if(intent.free&&e.is_free!==true)return null;
  if(intent.maxPrice!=null&&(e.price_min_ils==null||e.price_min_ils>intent.maxPrice))return null;
  if(intent.age!=null&&e.age_min!=null&&intent.age<e.age_min)return null;
  if(intent.age!=null&&e.age_max!=null&&intent.age>e.age_max)return null;
  const hay=eventSearchText(e),norm=hebrewSearchText(hay);
  let score=0,matchedConcepts=0,matchedTerms=0;
  for(const concept of intent.concepts){
    let points=concept.cats[e.category]||0;
    // Family searches should not recommend adult theatre or senior workshops
    // merely because these categories occasionally contain children's events.
    if(concept.id==="family"&&e.category!=="kids"&&
       !(e.audiences||[]).some(a=>["kids","families"].includes(a))&&
       !/ילד|פעוט|קטנט|משפח|גן חובה|נוער|בובות|שעת סיפור|לגילאי/.test(hay)){
      points=0;
    }
    if(textIncludesConcept(hay,concept.eventWords))points+=5;
    if(concept.id==="family"&&(e.audiences||[]).some(a=>["kids","families"].includes(a)))points+=8;
    if(concept.id==="family"&&/הורה ילד|ילדי|ילדים|פעוט|גן חובה/.test(hay))points+=7;
    if(concept.id==="outdoors"&&/חוף|ים|פארק|גלישה|טיילת|שטח/.test(hay))points+=8;
    if(concept.id==="dateNight"&&/אהבה|זוגי|רומנטי/.test(hay))points+=7;
    if(concept.id==="seniors"&&(e.audiences||[]).includes("seniors"))points+=8;
    if(points){score+=points;matchedConcepts++}
  }
  for(const term of intent.terms){
    const forms=searchWordForms(term);
    const title=hebrewSearchText(e.title||"");
    const venue=hebrewSearchText(e.venue||"");
    if(forms.some(w=>w.length>=2&&(title.includes(w)||norm.startsWith(w)))){score+=22;matchedTerms++;continue}
    if(forms.some(w=>w.length>=2&&venue.includes(w))){score+=14;matchedTerms++;continue}
    if(forms.some(w=>w.length>=2&&norm.includes(w))){score+=9;matchedTerms++;continue}
    if(forms.some(w=>w.length>=4&&fuzzyTokenMatch(w,norm))){score+=5;matchedTerms++;continue}
  }
  const recognized=intent.concepts.length>0||intent.terms.length>0;
  if(intent.concepts.length>0&&matchedConcepts===0&&matchedTerms===0)return null;
  // A name/venue in the query is a required signal, not just a weak preference.
  if(intent.terms.length>0&&matchedTerms===0)return null;
  if(!recognized)score=2;
  if(score<=0)return null;
  if(intent.terms.length>1&&matchedTerms<intent.terms.length)score-=4*(intent.terms.length-matchedTerms);
  if(intent.concepts.length>1&&matchedConcepts<intent.concepts.length)score-=6*(intent.concepts.length-matchedConcepts);
  if(e.start_date>=iso(today()))score+=3;
  return score;
}
function searchIntentLabel(intent){
  const labels=intent.concepts.slice(0,3).map(x=>x.label);
  if(intent.date)labels.push(({today:"היום",tomorrow:"מחר",weekend:"בסוף השבוע",week:"השבוע",month:"החודש"})[intent.date]);
  if(intent.free)labels.push("בחינם");
  if(intent.age!=null)labels.push("לגיל "+intent.age);
  return labels.join(" · ");
}
function preciseSubcategoryIntent(query){
  const q=hebrewSearchText(query);
  if(/קונצרט/.test(q))return {category:"music",subcategory:"concerts",token:/קונצרט|תזמורת|סימפוני|פילהרמונ/};
  if(/הצגת ילדי|הצגות ילדי|תיאטרונ ילדי/.test(q))return {category:"kids",subcategory:"kids-theatre",token:/הצג|תיאטרונ|מחז/};
  if(/שעת סיפור/.test(q))return {category:"kids",subcategory:"story-time",token:/שעת סיפור/};
  return null;
}
function matchesPreciseIntent(event,rule){
  if(!rule)return true;
  if(event.category!==rule.category)return false;
  if(event.subcategory===rule.subcategory)return true;
  if(event.subcategory)return false;
  // Legacy records without a subtype: admit only explicit contextual title evidence.
  return rule.token.test(hebrewSearchText(event.title||""));
}
function filtered(){
  const q=state.query.trim(),intent=q?parseSearchIntent(q):null;
  let arr=state.events.filter(e=>{
    if(isPersistentExhibition(e)&&state.category!=="exhibition")return false;
    if(q && !matchesPreciseIntent(e,preciseSubcategoryIntent(q)))return false;
    if(q){
      // A new conversational query stands on its own; older quick/date/category selections
      // must not silently erase relevant recommendations.
      return e.start_date>=iso(today())&&eventSemanticScore(e,intent)!=null;
    }
    if(!matchesQuick(e))return false;
    if(state.date&&e.start_date!==state.date)return false;
    if(state.periodStart&&state.periodEnd&&(e.start_date<state.periodStart||e.start_date>state.periodEnd))return false;
    if(state.category&&e.category!==state.category)return false;
    if(state.subcategory&&e.subcategory!==state.subcategory)return false;
    if(state.category==="sport"){
      if(state.sportBranch!=="all"&&sportKey(e)!==state.sportBranch)return false;
      if(state.sportTeam!=="all"&&sportTeamConfig(e)?.id!==state.sportTeam)return false;
    }
    if(state.favoritesOnly&&!favorites.has(e.event_id))return false;
    return true;
  });
  if(q)arr.sort((a,b)=>{
    const delta=eventSemanticScore(b,intent)-eventSemanticScore(a,intent);
    return delta||(a.start_date+(a.start_time||"99:99")).localeCompare(b.start_date+(b.start_time||"99:99"));
  });
  else if(state.sort==="priceLow")arr.sort((a,b)=>(a.price_min_ils??999999)-(b.price_min_ils??999999)||a.start_date.localeCompare(b.start_date));
  else if(state.sort==="priceHigh")arr.sort((a,b)=>(b.price_min_ils??-1)-(a.price_min_ils??-1)||a.start_date.localeCompare(b.start_date));
  else arr.sort((a,b)=>(a.start_date+(a.start_time||"99:99")).localeCompare(b.start_date+(b.start_time||"99:99")));
  return groupEvents(arr);
}

function calendarEventCounts(){
  const counts={};
  state.events.forEach(e=>counts[e.start_date]=(counts[e.start_date]||0)+1);
  return counts;
}
function calendarMonthOptions(){
  const t=today(),start=firstOfMonth(t);
  const eventDates=state.events.map(e=>localDate(e.start_date)).filter(d=>!Number.isNaN(d.getTime()));
  const latest=eventDates.length?new Date(Math.max(...eventDates.map(d=>d.getTime()))):start;
  const floor=addMonths(start,18);
  let end=latest>floor?firstOfMonth(latest):floor;
  if(state.calendarMonth&&firstOfMonth(state.calendarMonth)>end)end=firstOfMonth(state.calendarMonth);
  const out=[];
  for(let d=new Date(start);d<=end;d=addMonths(d,1))out.push(new Date(d));
  return out;
}
function ensureCalendarState(){
  const t=today();
  if(!state.calendarWeek)state.calendarWeek=startOfWeek(t);
  if(!state.calendarMonth)state.calendarMonth=firstOfMonth(t);
}
function resetCalendarToToday(){
  const t=today();
  state.calendarWeek=startOfWeek(t);
  state.calendarMonth=firstOfMonth(t);
}
function renderDates(){
  ensureCalendarState();
  const calendarBox=$("calendarBox"),resetButton=$("resetDate");
  if(calendarBox)calendarBox.hidden=state.calendarCollapsed;
  if(resetButton){
    resetButton.hidden=!state.calendarCollapsed;
    resetButton.innerHTML='<svg class="calendarOpenIcon" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/><path d="m9 16 2 2 4-4"/></svg><span>בחרו תאריך</span>';
    resetButton.classList.add("calendarOpenButton");
  }
  if(state.calendarCollapsed)return;

  const rail=$("dateRail"),monthGrid=$("monthGrid"),weekBox=$("weekCalendar"),monthBox=$("monthCalendar");
  const label=$("calendarPeriodLabel"),select=$("calendarMonthSelect");
  if(!rail||!monthGrid||!weekBox||!monthBox||!label||!select)return;

  const t=today(),counts=calendarEventCounts();
  const monthFmt=new Intl.DateTimeFormat("he-IL",{month:"long",year:"numeric"});
  const dayFmt=new Intl.DateTimeFormat("he-IL",{weekday:"short"});
  const shortMonthFmt=new Intl.DateTimeFormat("he-IL",{month:"short"});

  const options=calendarMonthOptions();
  select.innerHTML=options.map(d=>'<option value="'+iso(d)+'"'+(sameMonth(d,state.calendarMonth)?' selected':'')+'>'+escapeHtml(monthFmt.format(d))+'</option>').join("");

  $("weekViewButton")?.classList.toggle("is-active",state.calendarMode==="week");
  $("monthViewButton")?.classList.toggle("is-active",state.calendarMode==="month");
  weekBox.hidden=true;
  monthBox.hidden=state.calendarMode!=="month";

  if(state.calendarMode==="week"){
    const weekStart=new Date(state.calendarWeek),weekEnd=daysFrom(weekStart,6);
    const start=weekStart<t?t:weekStart;
    const end=weekEnd;
    label.textContent=fmtDate.format(start)+" – "+fmtDate.format(end);
    rail.innerHTML=Array.from({length:7},(_,i)=>daysFrom(start,i)).map(d=>{
      const id=iso(d),cnt=counts[id]||0,active=state.date===id?" is-active":"",past=d<t?" is-past":"";
      return '<button class="dateButton'+active+past+'" data-date="'+id+'" '+(d<t?'disabled':'')+'>'+
        '<small>'+escapeHtml(dayFmt.format(d))+'</small><b>'+d.getDate()+'</b>'+
        '<small>'+escapeHtml(shortMonthFmt.format(d))+'</small>'+
        (cnt?'<span class="dateCount">'+cnt+' אירועים</span>':'<span class="dateCount is-empty">אין אירועים</span>')+
      '</button>';
    }).join("");
    state.calendarMonth=firstOfMonth(weekStart);
    select.value=iso(state.calendarMonth);
  }else{
    const month=firstOfMonth(state.calendarMonth);
    label.textContent=monthFmt.format(month);
    const y=month.getFullYear(),m=month.getMonth();
    const last=new Date(y,m+1,0).getDate(),offset=month.getDay();
    const cells=[];
    for(let i=0;i<offset;i++)cells.push('<span class="monthDay monthDay--empty" aria-hidden="true"></span>');
    for(let day=1;day<=last;day++){
      const d=new Date(y,m,day),id=iso(d),cnt=counts[id]||0,active=state.date===id?" is-active":"",past=d<t?" is-past":"";
      cells.push('<button class="monthDay'+active+past+(cnt?' has-events':'')+'" data-date="'+id+'" '+(d<t?'disabled':'')+'>'+
        '<span class="monthDay__num">'+day+'</span>'+
        (cnt?'<span class="monthDay__count">'+cnt+'</span>':'')+
      '</button>');
    }
    monthGrid.innerHTML=cells.join("");
  }

  const apply=$("calendarApply"),selectionText=$("calendarSelectionText");
  if(apply&&selectionText){
    if(state.calendarMode==="week"){
      const weekStart=startOfWeek(state.calendarWeek),end=daysFrom(weekStart,6);
      const start=weekStart<t?t:weekStart;
      const count=state.events.filter(e=>e.start_date>=iso(start)&&e.start_date<=iso(end)).length;
      apply.textContent="הצג אירועי השבוע";
      selectionText.textContent=new Intl.DateTimeFormat("he-IL",{day:"numeric",month:"short"}).format(start)+" – "+new Intl.DateTimeFormat("he-IL",{day:"numeric",month:"short"}).format(end)+" · "+count+" אירועים";
    }else{
      const start=firstOfMonth(state.calendarMonth),end=new Date(start.getFullYear(),start.getMonth()+1,0);
      const count=state.events.filter(e=>e.start_date>=iso(start)&&e.start_date<=iso(end)).length;
      apply.textContent="הצג אירועי החודש";
      selectionText.textContent=new Intl.DateTimeFormat("he-IL",{month:"long",year:"numeric"}).format(start)+" · "+count+" אירועים";
    }
  }

  const currentBoundary=state.calendarMode==="week"?startOfWeek(t):firstOfMonth(t);
  const viewedBoundary=state.calendarMode==="week"?startOfWeek(state.calendarWeek):firstOfMonth(state.calendarMonth);
  $("calendarPrev").disabled=viewedBoundary<=currentBoundary;
}
function renderCategories(){
  const cats=["music","standup","kids","sport","theatre","lecture","workshop","exhibition","seniors","festival","community","cinema"];
  const counts={};groupEvents(state.events).forEach(e=>counts[e.category]=(counts[e.category]||0)+1);
  if(state.cinema.length)counts.cinema=state.cinema.length;
  $("categoryGrid").innerHTML=cats.map(c=>{
    const isCinema=c==="cinema";
    const active=isCinema?state.cinemaOpen:state.category===c;
    const label=isCinema?"קולנוע באשדוד":catLabels[c];
    const countLabel=(counts[c]||0)+" "+(isCinema?"סרטים":"אירועים");
    return '<button class="categoryCard '+(active?"is-active":"")+'" data-cat="'+c+'">'+
      '<span class="categoryCard__icon">'+catIcons[c]+'</span>'+
      '<span class="categoryCard__copy"><b>'+label+'</b><small>'+countLabel+'</small></span>'+
      '<span class="categoryCard__arrow">←</span>'+
    '</button>';
  }).join("");
}
function renderSubcategories(){
  const el=$("subcategoryNavigation");
  if(!el)return;
  const cat=window.publicTaxonomy?.find(c=>c.id===state.category);
  const subs=cat?.subcategories||[];
  if(!subs.length){el.hidden=true;el.innerHTML="";return}
  el.hidden=false;
  el.innerHTML='<strong>בחרו סוג אירוע</strong><div class="subcategoryOptions">'+
    '<button data-sub="" class="'+(!state.subcategory?'is-active':'')+'">הכול</button>'+
    subs.map(sub=>'<button data-sub="'+escapeHtml(sub.id)+'" class="'+(state.subcategory===sub.id?'is-active':'')+'">'+escapeHtml(sub.label)+'</button>').join("")+'</div>';
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
  const upcoming=state.events.filter(e=>localDate(e.start_date)>=today()&&e.ticket_status!=="sold_out"&&!isPersistentExhibition(e));
  const diverse=[],seen=new Set();
  for(const e of upcoming){if(!seen.has(e.category)){diverse.push(e);seen.add(e.category)} if(diverse.length>=6)break}
  const rotated=diverse.slice(state.discoverSeed%Math.max(1,diverse.length)).concat(diverse.slice(0,state.discoverSeed%Math.max(1,diverse.length)));
  return rotated.slice(0,5);
}
function hasActiveSelection(){
  return state.quick!=="all"||Boolean(state.date)||Boolean(state.periodStart)||Boolean(state.category)||Boolean(state.query.trim())||state.favoritesOnly||state.sort!=="date";
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
function renderSportsFilters(){
  const panel=$("sportsPanel");
  if(!panel)return;
  const open=state.category==="sport";
  panel.hidden=!open;
  if(!open)return;

  const sports=state.events.filter(e=>e.category==="sport"&&localDate(e.start_date)>=today());
  const teamCounts={},branchCounts={};
  sports.forEach(e=>{
    const t=sportTeamConfig(e),b=sportKey(e);
    if(t)teamCounts[t.id]=(teamCounts[t.id]||0)+1;
    branchCounts[b]=(branchCounts[b]||0)+1;
  });

  const teams=(state.sportsMeta?.teams||[]).filter(t=>teamCounts[t.id]);
  $("sportTeamFilters").innerHTML=
    '<button class="sportTeamButton sportTeamButton--all '+(state.sportTeam==="all"?"is-active":"")+'" data-sport-team="all"><span class="allSportsMark">★</span><span><b>כל הספורט</b><small>'+sports.length+' משחקים ואירועי ספורט</small></span></button>'+
    teams.map(t=>{
      const icons=(t.sports||[]).map(k=>sportBranchMeta(k).icon).join(" ");
      return '<button class="sportTeamButton '+(state.sportTeam===t.id?"is-active":"")+'" data-sport-team="'+escapeHtml(t.id)+'">'+
        teamLogoHTML(t,"sportTeamButton__logo")+
        '<span class="sportTeamButton__copy"><b>'+escapeHtml(t.name)+'</b><small>'+escapeHtml(icons)+' · '+teamCounts[t.id]+' משחקי בית</small></span>'+
      '</button>';
    }).join("");

  const branches=Object.entries(state.sportsMeta?.branches||{}).filter(([k])=>branchCounts[k]);
  $("sportBranchFilters").innerHTML=
    '<button class="'+(state.sportBranch==="all"?"is-active":"")+'" data-sport-branch="all"><span>◎</span>כל הענפים</button>'+
    branches.map(([k,b])=>'<button class="'+(state.sportBranch===k?"is-active":"")+'" data-sport-branch="'+escapeHtml(k)+'"><span>'+escapeHtml(b.icon)+'</span>'+escapeHtml(b.label)+' <small>'+branchCounts[k]+'</small></button>').join("");

  $("sportsReset").onclick=()=>{state.sportTeam="all";state.sportBranch="all";render()};
  $("sportTeamFilters").onclick=e=>{
    const b=e.target.closest("[data-sport-team]");if(!b)return;
    state.sportTeam=b.dataset.sportTeam;render();
    requestAnimationFrame(()=>$("eventsGrid")?.scrollIntoView({behavior:"smooth",block:"start"}));
  };
  $("sportBranchFilters").onclick=e=>{
    const b=e.target.closest("[data-sport-branch]");if(!b)return;
    state.sportBranch=b.dataset.sportBranch;render();
    requestAnimationFrame(()=>$("eventsGrid")?.scrollIntoView({behavior:"smooth",block:"start"}));
  };
}
function renderActiveFilters(){
  const x=[];
  if(state.quick!=="all")x.push({k:"quick",label:$("quickFilters").querySelector('[data-quick="'+state.quick+'"]')?.textContent||state.quick});
  if(state.date)x.push({k:"date",label:fmtFull.format(localDate(state.date))});
  if(state.periodStart&&state.periodEnd){
    const start=localDate(state.periodStart),end=localDate(state.periodEnd);
    const label=state.periodType==="month"
      ?new Intl.DateTimeFormat("he-IL",{month:"long",year:"numeric"}).format(start)
      :"השבוע "+new Intl.DateTimeFormat("he-IL",{day:"numeric",month:"short"}).format(start)+" – "+new Intl.DateTimeFormat("he-IL",{day:"numeric",month:"short"}).format(end);
    x.push({k:"period",label});
  }
  if(state.category)x.push({k:"category",label:catLabels[state.category]||state.category});
  if(state.subcategory)x.push({k:"subcategory",label:window.publicTaxonomy?.find(c=>c.id===state.category)?.subcategories?.find(x=>x.id===state.subcategory)?.label||state.subcategory});
  if(state.category==="sport"&&state.sportTeam!=="all"){
    const t=(state.sportsMeta?.teams||[]).find(x=>x.id===state.sportTeam);
    if(t)x.push({k:"sportTeam",label:t.name});
  }
  if(state.category==="sport"&&state.sportBranch!=="all"){
    const b=sportBranchMeta(state.sportBranch);
    x.push({k:"sportBranch",label:b.icon+" "+b.label});
  }
  if(state.query)x.push({k:"query",label:'"'+state.query+'"'});
  if(state.favoritesOnly)x.push({k:"favorites",label:"מועדפים"});
  $("activeFilters").innerHTML=x.map(i=>'<button class="filterChip" data-remove="'+i.k+'">'+escapeHtml(i.label)+' ×</button>').join("");
}
function renderResults(){
  const arr=filtered();
  $("eventsGrid").innerHTML=arr.map(eventCard).join("");
  const sports=state.category==="sport";
  const title=$("resultsTitle");
  const smartIntent=state.query.trim()?parseSearchIntent(state.query.trim()):null;
  if(title)title.textContent=smartIntent?"האפשרויות שמצאנו בשבילכם":sports?"משחקי הבית ואירועי הספורט באשדוד":"כל האירועים באשדוד";
  $("resultCount").textContent=arr.length+(smartIntent?" אפשרויות מתאימות":sports?" משחקים ואירועי ספורט נמצאו":" אירועים נמצאו");
  $("emptyState").hidden=arr.length>0;
  $("eventsGrid").hidden=arr.length===0;
  const feedback=$("searchFeedback");
  if(feedback){
    const query=state.query.trim();
    feedback.hidden=!query;
    const understood=query?searchIntentLabel(parseSearchIntent(query)):"";
    feedback.textContent=query?(arr.length?(understood?"הבנתי: "+understood+" · ":"")+arr.length+" אפשרויות · Enter להצגת התוצאות":"לא מצאתי כרגע התאמה טובה. נסו לשנות תאריך, נושא או שם אירוע."):"";
  }
}
function render(){
  document.querySelectorAll("#quickFilters button").forEach(b=>b.classList.toggle("is-active",b.dataset.quick===state.quick));
  $("favoritesOnly").setAttribute("aria-pressed",state.favoritesOnly?"true":"false");
  renderDates();renderCategories();renderSubcategories();renderHeroStats();renderSportsFilters();renderActiveFilters();renderResults();
  bindDynamic();
}
function bindDynamic(){
  document.querySelectorAll("[data-event]").forEach(el=>el.onclick=e=>{if(e.target.closest("[data-heart], [data-event-video], [data-cat], .dateStack__more"))return;location.href="event.html?id="+encodeURIComponent(el.dataset.event)});
  document.querySelectorAll("[data-heart]").forEach(b=>b.onclick=e=>{e.stopPropagation();toggleFavorite(b.dataset.heart)});
  document.querySelectorAll("[data-event-video]").forEach(b=>b.onclick=e=>{e.stopPropagation();openEventVideo(b.dataset.eventVideo)});
  document.querySelectorAll("[data-date]").forEach(b=>b.onclick=()=>{
    const next=state.date===b.dataset.date?null:b.dataset.date;
    window.ashdodAnalytics?.send("select_date",{selected_date:next || "all",selection_type:next ? "day" : "clear"});
    state.date=next;
    state.periodStart=null;state.periodEnd=null;state.periodType=null;
    state.quick="all";
    render();
    if(next)requestAnimationFrame(()=>$("eventsGrid")?.scrollIntoView({behavior:"smooth",block:"start"}));
  });
  document.querySelectorAll("#subcategoryNavigation [data-sub]").forEach(b=>b.onclick=()=>{
    state.subcategory=b.dataset.sub||null;
    render();
    requestAnimationFrame(()=>$("resultsTitle")?.scrollIntoView({behavior:"smooth",block:"start"}));
  });
  document.querySelectorAll("[data-cat]").forEach(b=>b.onclick=()=>{
    window.ashdodAnalytics?.send("select_category",{category:b.dataset.cat,category_name:catLabels[b.dataset.cat] || b.dataset.cat,selection_type:state.category===b.dataset.cat ? "clear" : "select"});
    if(b.dataset.cat==="cinema"){
      state.category=null;
      state.cinemaOpen=true;
      render();
      renderCinema();
      requestAnimationFrame(()=>$("cinemaSection")?.scrollIntoView({behavior:"smooth",block:"start"}));
      return;
    }
    state.cinemaOpen=false;
    renderCinema();
    const nextCategory=state.category===b.dataset.cat?null:b.dataset.cat;
    if(nextCategory!=="sport"){state.sportTeam="all";state.sportBranch="all"}
    state.category=nextCategory;
    state.subcategory=null;
    render();
    requestAnimationFrame(()=>{
      const target=state.category==="sport"?$("sportsPanel"):$("resultsTitle");
      target?.scrollIntoView({behavior:"smooth",block:"start"});
    });
  });
  document.querySelectorAll("[data-remove]").forEach(b=>b.onclick=()=>{
    const k=b.dataset.remove;
    if(k==="quick")state.quick="all";
    if(k==="date")state.date=null;
    if(k==="period"){state.periodStart=null;state.periodEnd=null;state.periodType=null}
    if(k==="subcategory")state.subcategory=null;
    if(k==="category"){state.subcategory=null;state.category=null;state.sportTeam="all";state.sportBranch="all"}
    if(k==="sportTeam")state.sportTeam="all";
    if(k==="sportBranch")state.sportBranch="all";
    if(k==="query"){state.query="";$("searchInput").value=""}
    if(k==="favorites")state.favoritesOnly=false;
    render()
  });
}
function modalScheduleText(e){
  const occ=eventOccurrences(e);
  return occ.map(x=>{
    const base=fmtFull.format(localDate(x.start_date))+' · '+formatTime(x.start_time);
    if(x.category==="sport"&&x.away_team)return base+" · מול "+x.away_team;
    return base;
  }).join(' | ');
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
function resetAll(){state.quick="all";state.date=null;state.periodStart=null;state.periodEnd=null;state.periodType=null;state.calendarCollapsed=true;state.category=null;state.subcategory=null;state.cinemaOpen=false;state.sportTeam="all";state.sportBranch="all";state.query="";state.favoritesOnly=false;state.sort="date";resetCalendarToToday();$("searchInput").value="";$("sortSelect").value="date";render();renderCinema()}

async function init(){
  const [data,fallbacks,cinema,sports,taxonomy]=await Promise.all([
    fetch("data/events.json",{cache:"no-store"}).then(r=>r.json()),
    fetch("category-fallbacks.json?v=20261005-21").then(r=>r.json()).catch(()=>({})),
    fetch("data/cinema.json",{cache:"no-store"}).then(r=>r.json()).catch(()=>({movies:[]})),
    fetch("data/sports.json?v=20261005-2").then(r=>r.json()).catch(()=>({branches:{},teams:[]})),
    fetch("../admin/data/taxonomy.json",{cache:"no-store"}).then(r=>r.json()).catch(()=>({primary_categories:[]}))
  ]);
  const horizon=addMonths(today(),5); horizon.setDate(today().getDate());
  state.events=(data.events||[]).filter(e=>e.start_date>=iso(today())&&e.start_date<=iso(horizon)&&!isNonEventActivity(e));
  state.fallbacks=fallbacks;
  state.generatedAt=data.generated_at||null;
  state.cinema=cinema.movies||[];
  state.cinemaUpdatedAt=cinema.updated_at||null;
  state.sportsMeta=sports||{branches:{},teams:[]};
  window.publicTaxonomy=taxonomy.primary_categories||[];
  const requestedCategory=new URLSearchParams(location.search).get("category");
  if(requestedCategory&&Object.prototype.hasOwnProperty.call(catLabels,requestedCategory))state.category=requestedCategory;
  const requestedSub=new URLSearchParams(location.search).get("subcategory");
  if(requestedSub&&window.publicTaxonomy.find(c=>c.id===state.category)?.subcategories?.some(x=>x.id===requestedSub))state.subcategory=requestedSub;
  if(location.hash==="#cinema")state.cinemaOpen=true;
  render();
  renderCinema();
  if(state.cinemaOpen)requestAnimationFrame(()=>$("cinemaSection")?.scrollIntoView({block:"start"}));
  const searchInput=$("searchInput");
  let searchTimer, lastMeasuredSearch = "";
  const measureSearch = () => {
    clearTimeout(searchTimer);
    const query = searchInput.value.trim();
    if (!query) { lastMeasuredSearch = ""; return; }
    if (query === lastMeasuredSearch) return;
    lastMeasuredSearch = query;
    const analytics = window.ashdodAnalytics;
    analytics?.send("search",{search_term:analytics.safeSearch(query),result_count:groupEvents(filtered()).length});
  };
  document.addEventListener("click", event => {
    if (!(event.target instanceof Element)) return;
    if (event.target.closest("[data-heart], [data-event-video]")) return;
    const card = event.target.closest("[data-event]");
    const link = event.target.closest('a[href*="event.html?id="]');
    let id = card?.dataset.event;
    if (link) id = new URL(link.href).searchParams.get("id");
    const selected = state.events.find(item => item.event_id === id);
    if (selected) window.ashdodAnalytics?.send("select_event",window.ashdodAnalytics.metadata(selected));
  },true);
  const showSearchResults=()=>{
    clearTimeout(searchTimer);
    state.query=searchInput.value.trim();
    state.quick="all";
    state.date=null;state.periodStart=null;state.periodEnd=null;state.periodType=null;
    state.category=null;state.sportTeam="all";state.sportBranch="all";
    state.cinemaOpen=false;
    state.favoritesOnly=false;
    render();
    renderCinema();
    measureSearch();
    requestAnimationFrame(()=>($("resultsTitle")||$("eventsGrid"))?.scrollIntoView({behavior:"smooth",block:"start"}));
  };
  searchInput.addEventListener("input",e=>{state.query=e.target.value;render();clearTimeout(searchTimer);searchTimer=setTimeout(measureSearch,900)});
  searchInput.addEventListener("keydown",e=>{
    if(e.key==="Enter"){e.preventDefault();showSearchResults()}
  });
  $("searchSubmit").onclick=showSearchResults;
  $("clearSearch").onclick=()=>{
    clearTimeout(searchTimer);lastMeasuredSearch="";
    state.query="";searchInput.value="";render();searchInput.focus();
  };
  $("quickFilters").onclick=e=>{
    const b=e.target.closest("[data-quick]");if(!b)return;
    if (["kids","standup","music","lecture","theatre"].includes(b.dataset.quick)) window.ashdodAnalytics?.send("select_category",{category:b.dataset.quick,selection_type:"quick_filter"});
    if (["today","tomorrow","weekend"].includes(b.dataset.quick)) window.ashdodAnalytics?.send("select_date",{selection_type:b.dataset.quick});
    state.quick=b.dataset.quick;state.date=null;state.periodStart=null;state.periodEnd=null;state.periodType=null;render()
  };
  const clearCalendarSelection=()=>{
    state.date=null;
    state.periodStart=null;
    state.periodEnd=null;
    state.periodType=null;
    state.quick="all";
    state.calendarCollapsed=true;
    resetCalendarToToday();
    render();
    requestAnimationFrame(()=>$("eventsGrid")?.scrollIntoView({behavior:"smooth",block:"start"}));
  };
  $("resetDate").onclick=()=>{
    if(state.calendarCollapsed){
      state.calendarCollapsed=false;
      renderDates();
      requestAnimationFrame(()=>$("calendarBox")?.scrollIntoView({behavior:"smooth",block:"nearest"}));
      return;
    }
    clearCalendarSelection();
  };
  $("calendarAllDates").onclick=clearCalendarSelection;
  $("weekViewButton").onclick=()=>{
    state.calendarMode="week";
    if(state.date)state.calendarWeek=startOfWeek(localDate(state.date));
    renderDates();bindDynamic();
  };
  $("monthViewButton").onclick=()=>{
    state.calendarMode="month";
    if(state.date)state.calendarMonth=firstOfMonth(localDate(state.date));
    else if(state.calendarWeek)state.calendarMonth=firstOfMonth(state.calendarWeek);
    renderDates();bindDynamic();
  };
  $("calendarPrev").onclick=()=>{
    ensureCalendarState();
    if(state.calendarMode==="week")state.calendarWeek=daysFrom(state.calendarWeek,-7);
    else state.calendarMonth=addMonths(state.calendarMonth,-1);
    renderDates();bindDynamic();
  };
  $("calendarNext").onclick=()=>{
    ensureCalendarState();
    if(state.calendarMode==="week")state.calendarWeek=daysFrom(state.calendarWeek,7);
    else state.calendarMonth=addMonths(state.calendarMonth,1);
    renderDates();bindDynamic();
  };
  $("calendarMonthSelect").onchange=e=>{
    const selected=localDate(e.target.value);
    state.calendarMonth=firstOfMonth(selected);
    state.calendarMode="month";
    renderDates();bindDynamic();
  };
  $("calendarApply").onclick=()=>{
    ensureCalendarState();
    state.calendarCollapsed=false;
    state.date=null;
    state.quick="all";
    if(state.calendarMode==="week"){
      const start=startOfWeek(state.calendarWeek),end=daysFrom(start,6);
      state.periodStart=iso(start);state.periodEnd=iso(end);state.periodType="week";
    }else{
      const start=firstOfMonth(state.calendarMonth),end=new Date(start.getFullYear(),start.getMonth()+1,0);
      state.periodStart=iso(start);state.periodEnd=iso(end);state.periodType="month";
    }
    window.ashdodAnalytics?.send("select_date",{selection_type:state.periodType,date_start:state.periodStart,date_end:state.periodEnd});
    render();
    requestAnimationFrame(()=>$("eventsGrid")?.scrollIntoView({behavior:"smooth",block:"start"}));
  };

  $("favoritesOnly").onclick=()=>{state.favoritesOnly=!state.favoritesOnly;render()};
  $("sortSelect").onchange=e=>{state.sort=e.target.value;render()};
  $("resetAll").onclick=resetAll;
  $("cinemaFilters").onclick=e=>{
    const b=e.target.closest("[data-cinema]"); if(!b)return;
    state.cinemaVenue=b.dataset.cinema; renderCinema();
  };
  $("cinemaAudienceFilters").onclick=e=>{
    const b=e.target.closest("[data-audience]"); if(!b)return;
    state.cinemaAudience=b.dataset.audience; renderCinema();
  };
  $("cinemaClose").onclick=()=>{
    state.cinemaOpen=false;
    renderCinema();
    renderCategories();
    $("categoryGrid")?.scrollIntoView({behavior:"smooth",block:"center"});
  };
  document.querySelectorAll("[data-close-trailer]").forEach(x=>x.onclick=closeTrailer);
  document.querySelectorAll("[data-close-modal]").forEach(x=>x.onclick=closeModal);
  $("modalFavorite").onclick=()=>{toggleFavorite($("modalFavorite").dataset.id);openEvent($("modalFavorite").dataset.id)};
  document.addEventListener("keydown",e=>{if(e.key==="Escape"){closeModal();closeTrailer()} });
}
init().catch(err=>{console.error(err);$("eventsGrid").innerHTML='<div class="emptyState"><h3>לא הצלחנו לטעון את האירועים</h3><p>נסו לרענן את העמוד.</p></div>'});

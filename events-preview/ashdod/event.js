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
  const vocabulary = new Set("לאן לצאת מה עושים עם הילדים ילדים ילד ילדה משפחה משפחות היום מחר השבוע סוף שבוע סופש בסופש חינם זול הופעות הופעה מוזיקה מוסיקה סטנדאפ תיאטרון הצגות הצגה קולנוע סרט סרטים הרצאות הרצאה סדנאות סדנה יצירה אמנות אומנות תערוכות תערוכה פסטיבל פסטיבלים קהילה ספורט כדורגל כדורסל כדוריד כדורעף גלישה טיולים טבע פארקים פארק חופים חוף ים אשדוד באשדוד מבוגרים למבוגרים זוג זוגות ערב בוקר צהריים בילוי בילויים לנוער נוער לילדים קטנים קטנות".split(" "));
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

const $=id=>document.getElementById(id);
const catLabels={
  music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים ומשפחה",theatre:"תיאטרון",
  lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",
  festival:"פסטיבלים",community:"קהילה",sport:"ספורט באשדוד",tour:"סיורים",other:"אירוע"
};
let sportsMeta={branches:{},teams:[]};
const fmtFull=new Intl.DateTimeFormat("he-IL",{weekday:"long",day:"numeric",month:"long",year:"numeric"});
const fmtMonth=new Intl.DateTimeFormat("he-IL",{month:"short"});
const currency=new Intl.NumberFormat("he-IL",{style:"currency",currency:"ILS",maximumFractionDigits:0});

function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function normalizeSearch(s){
  return String(s||"").toLowerCase()
    .replace(/[״"'׳.,!?():;\/\-–—]/g," ")
    .replace(/\s+/g," ").trim();
}
function eventGroupKey(e){
  if(e?.series_id)return "series:"+String(e.series_id);
  return normalizeSearch(e?.title||"");
}
function eventDisplayTitle(e){
  return e?.series_title||e?.title||"אירוע";
}
function localDate(s){const [y,m,d]=String(s||"").split("-").map(Number);return new Date(y,m-1,d)}
function formatTime(t){return t||"השעה תפורסם"}
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
  return sportsMeta?.branches?.[key]||{label:"ספורט",icon:"⚑"};
}
function sportTeamConfig(e){
  const home=String(e?.home_team||"").trim(),key=sportKey(e);
  return (sportsMeta?.teams||[]).find(t=>(t.match_home_teams||[]).includes(home)&&(!(t.sports||[]).length||(t.sports||[]).includes(key)))||null;
}
function teamInitials(name){
  return String(name||"קבוצה").split(/\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join("");
}
function isRepresentativeHomeGame(e){
  return e?.category==="sport"&&e?.is_home_game===true&&e?.representative_team===true&&Boolean(e?.home_team);
}
function sportHeroFallback(e){
  const team=sportTeamConfig(e),branch=sportBranchMeta(e),name=team?.name||e.home_team||"ספורט באשדוד";
  const logo=team?.logo_url?'<img src="'+escapeHtml(team.logo_url)+'" alt="" onerror="this.remove()">':'<b>'+escapeHtml(teamInitials(name))+'</b>';
  return '<div class="fallback sportHeroFallback"><span class="sportHeroLogo">'+logo+'</span><span class="sportHeroBranch">'+escapeHtml(branch.icon)+' '+escapeHtml(branch.label)+'</span><strong>'+escapeHtml(name)+'</strong><small>משחק בית באשדוד</small></div>';
}
function purchaseAction(e){
  const url=String(e.purchase_url||e.ticket_url||"").trim();
  if(/^https:\/\//i.test(url)){
    return {href:url,label:e.ticket_status==="sold_out"?"לפרטים באתר המקור":"לפרטים ולהזמנה",kind:"url",soldOut:e.ticket_status==="sold_out"};
  }
  if(e.ticket_status==="sold_out")return null;
  const phone=String(e.purchase_phone||"").trim().replace(/[^0-9+]/g,"");
  if(phone)return {href:"tel:"+phone,label:"צרו קשר",kind:"phone"};
  return null;
}
function groupPurchaseAction(occ){
  for(const e of occ){
    const a=purchaseAction(e);
    if(a)return a;
  }
  return null;
}
function trustedImage(e){
  return Boolean(e.image_url&&e.image_publishable===true&&e.image_verified===true);
}
function bestImageEvent(occ){
  return occ.find(e=>trustedImage(e)&&e.thumbnail_ready===true)
    ||occ.find(e=>trustedImage(e))
    ||occ[0];
}
function richEvent(occ){
  return occ.find(e=>e.rich_content_status==="enriched")
    ||occ.find(e=>e.long_description||e.short_pitch||e.youtube_id)
    ||occ[0];
}
function uniqueByTitle(events){
  const seen=new Set(),out=[];
  for(const e of events){
    const k=eventGroupKey(e);
    if(seen.has(k))continue;
    seen.add(k);out.push(e);
  }
  return out;
}
function directEventUrl(id){return "event.html?id="+encodeURIComponent(id)}
function splitParagraphs(text){
  return String(text||"").split(/\n\s*\n/).map(x=>x.trim()).filter(Boolean);
}
function categoryExperience(e){
  const map={
    music:"ערב של מוזיקה והופעה חיה",
    standup:"ערב של סטנדאפ והומור",
    kids:"בילוי לילדים ולמשפחה",
    theatre:"ערב של תיאטרון ובמה",
    lecture:"מפגש של תוכן, ידע והשראה",
    exhibition:"בילוי של אמנות ותרבות",
    workshop:"פעילות מעשית וסדנה",
    cinema:"אירוע קולנוע והקרנה",
    festival:"אירוע פסטיבל וחוויה עירונית",
    community:"מפגש קהילתי",
    sport:"משחק בית או אירוע ספורטיבי בעיר",
    tour:"סיור וחוויה בעיר"
  };
  return map[e.category]||"אירוע תרבות ופנאי";
}
function autoPitch(e){
  const where=e.venue&&e.venue!=="אשדוד"?" • "+e.venue:"";
  return e.title+where+" • "+fmtFull.format(localDate(e.start_date))+" • "+formatTime(e.start_time)+
    (e.ticket_status==="sold_out"?" • הכרטיסים אזלו":"");
}
function meaningfulEventDescription(e){
  // Prefer editorial descriptions already attributed to this event.
  // A short pitch is shown only when it adds information beyond the title.
  const candidates=[e.long_description,e.series_description,e.description,e.short_pitch];
  return candidates.map(v=>String(v||"").trim()).find(v=>
    v.length>=25 &&
    !v.includes("תיאור מפורט של האירוע לא פורסם") &&
    !v.includes("המועד, המחיר, המיקום ודרכי יצירת הקשר מופיעים")
  )||"";
}
function autoHighlights(e,occ){
  const items=[];
  if(occ.length>1)items.push(occ.length+" מועדים לבחירה באשדוד");
  else items.push("מועד האירוע מרוכז וברור בעמוד");
  if(e.venue)items.push("מיקום: "+e.venue);
  else items.push("פרטי המקום יתעדכנו עם פרסומם");
  if(groupPurchaseAction(occ))items.push("קישור רכישה ישיר זמין מהעמוד");
  else items.push("פרטי רכישה יעודכנו לאחר אימות");
  return items;
}
function autoSuitability(e){
  const map={
    music:"מתאים למי שמחפש ערב מוזיקלי ובילוי תרבותי באשדוד.",
    standup:"מתאים למי שמחפש ערב סטנדאפ והומור. יש לבדוק מגבלת גיל אצל המארגן לפני רכישה.",
    kids:"מתאים למשפחות וילדים; מומלץ לבדוק את טווח הגילים המדויק אצל המארגן.",
    theatre:"מתאים לחובבי הצגות, במה ותיאטרון.",
    lecture:"מתאים למי שמחפש הרצאה, העשרה ותוכן.",
    exhibition:"מתאים לחובבי אמנות, תרבות ותערוכות.",
    workshop:"מתאים למי שמחפש פעילות מעשית או סדנה.",
    cinema:"מתאים למי שמחפש הקרנה או אירוע קולנוע.",
    community:"מתאים למי שמחפש פעילות ומפגש קהילתי בעיר.",
    sport:"מתאים למי שמחפש פעילות ספורטיבית; מומלץ לבדוק דרישות השתתפות אצל המארגן.",
    festival:"מתאים למי שמחפש אירוע עירוני רחב וחוויית בילוי.",
    tour:"מתאים למי שמחפש סיור או פעילות היכרות עם העיר."
  };
  return map[e.category]||"מתאים למי שמחפש בילוי, תרבות ופנאי באשדוד.";
}

function renderHero(e,occ,imageEvent){
  const displayTitle=eventDisplayTitle(e);
  document.title=displayTitle+" | מה עושים באשדוד?";
  const desc=e.short_pitch||e.series_description||e.description||autoPitch({...e,title:displayTitle});
  document.querySelector('meta[name="description"]').setAttribute("content",desc);

  const sportBadge=e.category==="sport"?sportBranchMeta(e):null;
  $("heroBadges").innerHTML=
    '<span class="badge accent">'+escapeHtml(catLabels[e.category]||"אירוע")+'</span>'+
    (sportBadge?'<span class="badge">'+escapeHtml(sportBadge.icon)+' '+escapeHtml(sportBadge.label)+'</span>':"")+
    (occ.every(x=>x.ticket_status==="sold_out")?'<span class="badge badge--soldout">אזלו הכרטיסים</span>':"")+
    (occ.length>1?'<span class="badge">'+occ.length+' מועדים באשדוד</span>':"");
  $("eventTitle").textContent=displayTitle;
  $("eventPitch").textContent=e.short_pitch||e.series_description||e.description||autoPitch({...e,title:displayTitle});

  const venues=[...new Set(occ.map(x=>x.venue).filter(Boolean))];
  const dates=[...new Set(occ.map(x=>x.start_date).filter(Boolean))];
  $("heroMeta").innerHTML=[
    venues[0]||"המיקום יפורסם",
    dates.length>1?dates.length+" תאריכים":fmtFull.format(localDate(occ[0].start_date)),
    e.duration_minutes?e.duration_minutes+" דקות":null
  ].filter(Boolean).map(x=>'<span>'+escapeHtml(x)+'</span>').join("");

  if(trustedImage(imageEvent)){
    const src=imageEvent.thumbnail_ready&&imageEvent.thumbnail_url?imageEvent.thumbnail_url:imageEvent.image_url;
    $("heroImage").innerHTML='<img src="'+escapeHtml(src)+'" alt="'+escapeHtml(eventDisplayTitle(e))+'">';
  }else{
    if(e.category==="lecture"){
      const key=String(e.event_id||e.title||"");
      const theme=[...key].reduce((n,c)=>(n*29+c.charCodeAt(0))>>>0,3)%6;
      $("heroImage").innerHTML='<div class="fallback detailLectureArt detailLectureArt--'+theme+'">'+
        '<span class="detailLectureArt__symbol" aria-hidden="true">✦</span><strong>'+escapeHtml(eventDisplayTitle(e))+
        '</strong><small>איור להמחשה</small></div>';
    }else{
      $("heroImage").innerHTML=isRepresentativeHomeGame(e)?sportHeroFallback(e):'<div class="fallback">'+escapeHtml(eventDisplayTitle(e))+'</div>';
    }
  }

  const action=groupPurchaseAction(occ);
  if(action){
    const a=$("heroBuy");
    a.href=action.href;a.textContent=action.label;a.style.display="inline-flex";
    if(action.kind==="phone")a.removeAttribute("target");else a.target="_blank";
    const soldOut=occ.every(x=>x.ticket_status==="sold_out");
    $("heroBuyNote").hidden=!soldOut;
    if(soldOut)$("heroBuyNote").textContent="הכרטיסים לאירוע אזלו. אפשר לצפות בפרטים באתר המקור ולפנות למקום לבירור.";
  }else{
    $("heroBuy").style.display="none";
    $("heroBuyNote").hidden=false;
    $("heroBuyNote").textContent="אין כרגע קישור רכישה ישיר מאומת. נוסיף אותו ברגע שנוכל לאמת יעד רכישה ישיר.";
  }
}

function renderStory(e,occ){
  const description=meaningfulEventDescription(e);
  const paragraphs=splitParagraphs(description);
  // Never display generic placeholder copy as event editorial content.
  // Schedule, venue, prices and organizer contact remain in their own cards.
  $("aboutSection").hidden=!paragraphs.length;
  $("eventStory").innerHTML=paragraphs.map(p=>'<p>'+escapeHtml(p)+'</p>').join("");

  // Do not fabricate marketing claims when only ticket metadata is available.
  const highlights=Array.isArray(e.highlights)?e.highlights:[];
  const suitability=String(e.suitability||"").trim();
  $("highlightsSection").hidden=!highlights.length&&!suitability;
  $("highlights").innerHTML=highlights.map(x=>'<div class="highlight">'+escapeHtml(x)+'</div>').join("");
  $("suitability").textContent=suitability;
  $("suitability").hidden=!suitability;
}

function renderVideo(e){
  if(!e.youtube_id){
    $("videoSection").hidden=true;return;
  }
  $("videoSection").hidden=false;
  $("youtubeFrame").src="https://www.youtube-nocookie.com/embed/"+encodeURIComponent(e.youtube_id)+"?rel=0";
  $("youtubeFrame").title=e.youtube_title||("וידאו - "+e.title);
  $("youtubeTitle").textContent=e.youtube_title||"וידאו מהמופע";
  $("youtubeNote").textContent=e.youtube_note||"";
}

function renderPeople(e){
  const performers=Array.isArray(e.performers)?e.performers:[];
  const creators=Array.isArray(e.creators)?e.creators:[];
  if(!performers.length&&!creators.length){
    $("peopleSection").hidden=true;return;
  }
  $("peopleSection").hidden=false;
  let html="";
  if(performers.length){
    html+='<div class="peopleBlock"><h3>על הבמה</h3><ul>'+performers.map(x=>'<li>'+escapeHtml(x)+'</li>').join("")+'</ul></div>';
  }
  if(creators.length){
    html+='<div class="peopleBlock"><h3>יוצרים</h3><ul>'+creators.map(x=>'<li>'+escapeHtml(x)+'</li>').join("")+'</ul></div>';
  }
  $("peopleGrid").innerHTML=html;
}

function renderSchedule(occ){
  const groupAction=groupPurchaseAction(occ);
  $("scheduleList").innerHTML=occ.map(e=>{
    const d=localDate(e.start_date);
    const own=purchaseAction(e)||groupAction;
    return '<div class="scheduleItem">'+
      '<div class="scheduleDate"><b>'+String(d.getDate()).padStart(2,"0")+'</b><span>'+escapeHtml(fmtMonth.format(d))+'</span></div>'+
      '<div class="scheduleCopy"><b>'+escapeHtml(fmtFull.format(d))+'</b>'+
        (e.variant_label?'<strong class="scheduleVariant">'+escapeHtml(e.variant_label)+'</strong>':"")+
        '<span>'+escapeHtml(formatTime(e.start_time))+' · '+escapeHtml(e.venue||"המיקום יפורסם")+'</span>'+
        (own?'<a class="scheduleBuy" href="'+escapeHtml(own.href)+'" '+(own.kind==="url"?'target="_blank" rel="noopener"':'')+'>'+(e.ticket_status==="sold_out"?"אזלו הכרטיסים · לפרטי המקור ←":"לפרטים ולהזמנה ←")+'</a>':"")+
      '</div>'+
    '</div>';
  }).join("");
}

function renderPractical(e,occ){
  const venues=[...new Set(occ.map(x=>x.venue).filter(Boolean))];
  const prices=occ.map(priceText);
  const onePrice=[...new Set(prices)].length===1?prices[0]:"המחיר משתנה לפי מועד";
  const audience=(Array.isArray(e.audiences)&&e.audiences.length)?e.audiences.join(", "):null;
  const age=e.age_min!=null?"מגיל "+e.age_min:null;
  const rows=[
    ["מקום",venues.filter(v=>v!==e.city).join(" / ")||"המיקום המדויק לא פורסם במקור"],
    ...(e.address?[["כתובת",e.address]]:[]),
    ["מחיר",onePrice],
    ["כרטיסים",occ.every(x=>x.ticket_status==="sold_out")?"אזלו הכרטיסים":"יש לבדוק זמינות באתר המקור"],
    ...(e.duration_minutes?[["משך",e.duration_minutes+" דקות"]]:[]),
    ...(age?[["גילים",age]]:[]),
    ...(audience?[["קהל",audience]]:[]),
    ...(e.organizer?[["מארגן",e.organizer]]:[]),
    ...(e.ticket_provider?[["מערכת כרטיסים",e.ticket_provider]]:[]),
    ["מספר מועדים",String(occ.length)]
  ];
  const info=rows.map(([a,b])=>'<div class="infoRow"><b>'+escapeHtml(a)+'</b><span>'+escapeHtml(b)+'</span></div>').join("");
  const contact=String(e.contact_phone||e.purchase_phone||"").replace(/[^0-9+*]/g,"");
  const contactHtml=contact?'<div class="infoRow"><b>טלפון לבירורים</b><a href="tel:'+escapeHtml(contact)+'">'+escapeHtml(e.contact_phone||e.purchase_phone)+'</a>'+(e.contact_phone_secondary?'<a class="contactSecondary" href="tel:'+escapeHtml(String(e.contact_phone_secondary).replace(/[^0-9+]/g,""))+'">'+escapeHtml(e.contact_phone_secondary)+'</a>':"")+'</div>':"";
  const venueAddress=e.address||(e.venue&&e.venue!=="אשדוד"?e.venue:"");
  const maps=venueAddress?'<div class="infoRow"><b>ניווט</b><a href="https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(venueAddress)+'" target="_blank" rel="noopener">לפתיחת מפה ←</a></div>':"";
  const origin=String(e.ticket_url||e.purchase_url||"");
  const source=origin.startsWith("https://")?'<div class="infoRow"><b>מקור רשמי</b><a href="'+escapeHtml(origin)+'" target="_blank" rel="noopener">לעמוד האירוע ←</a></div>':"";
  const safeOperator=/^[a-z0-9_]+$/.test(e.operator_id||"")?e.operator_id:null;
  const operatorPage=safeOperator?'<div class="infoRow"><b>כל הפעילויות של המפעיל</b>'+
    '<a href="operator.html?id='+encodeURIComponent(safeOperator)+'">'+escapeHtml(e.operator_name||e.organizer||"כל הפעילויות")+' ←</a></div>':"";
  const email=e.contact_email?'<div class="infoRow"><b>דואר אלקטרוני</b>'+
    '<a href="mailto:'+escapeHtml(e.contact_email)+'">'+escapeHtml(e.contact_email)+'</a></div>':"";
  const venuePhone=e.venue_phone&&e.venue_phone!==e.contact_phone?
    '<div class="infoRow"><b>טלפון המקום</b><a href="tel:'+escapeHtml(e.venue_phone.replace(/[^0-9+*]/g,""))+'">'+escapeHtml(e.venue_phone)+'</a></div>':"";
  $("practicalInfo").innerHTML=info+contactHtml+venuePhone+email+maps+operatorPage+source;
}
function renderRelated(current,all){
  const currentKey=eventGroupKey(current);
  const related=uniqueByTitle(
    all.filter(e=>eventGroupKey(e)!==currentKey&&e.category===current.category)
      .sort((a,b)=>(a.start_date+(a.start_time||"99:99")).localeCompare(b.start_date+(b.start_time||"99:99")))
  ).slice(0,3);

  if(!related.length){$("relatedSection").hidden=true;return}
  $("relatedGrid").innerHTML=related.map(e=>{
    const img=e.thumbnail_ready&&e.thumbnail_url?e.thumbnail_url:(trustedImage(e)?e.image_url:null);
    return '<a class="relatedCard" href="'+directEventUrl(e.event_id)+'">'+
      '<div class="relatedCard__media">'+(img?'<img src="'+escapeHtml(img)+'" alt="">':'')+'</div>'+
      '<div class="relatedCard__body"><h3>'+escapeHtml(eventDisplayTitle(e))+'</h3><span>'+escapeHtml(fmtFull.format(localDate(e.start_date)))+'</span></div>'+
    '</a>';
  }).join("");
}

async function init(){
  try{
    const id=new URLSearchParams(location.search).get("id");
    if(!id)throw new Error("missing id");
    const [data,sports,editorial]=await Promise.all([
      fetch("data/events.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("data");return r.json()}),
      fetch("data/sports.json?v=20261005-2").then(r=>r.json()).catch(()=>({branches:{},teams:[]})),
      fetch("data/editorial.json",{cache:"no-store"}).then(r=>r.ok?r.json():{events:{}}).catch(()=>({events:{}}))
    ]);
    sportsMeta=sports||{branches:{},teams:[]};
    const editorialById=editorial?.events||{};
    const all=(data.events||[]).map(event=>{
      const entry=editorialById[event.event_id];
      if(!entry||typeof entry!=="object")return event;
      const allowed={};
      for(const field of ["long_description","short_pitch","youtube_title","youtube_note","suitability"]){
        if(typeof entry[field]==="string"&&entry[field].trim())allowed[field]=entry[field].trim();
      }
      if(Array.isArray(entry.performers))allowed.performers=entry.performers.filter(x=>typeof x==="string");
      if(Array.isArray(entry.creators))allowed.creators=entry.creators.filter(x=>typeof x==="string");
      if(Array.isArray(entry.highlights))allowed.highlights=entry.highlights.filter(x=>typeof x==="string");
      // Do not embed search results or unverified YouTube IDs.
      if(/^[a-zA-Z0-9_-]{11}$/.test(entry.youtube_id||"") && entry.video_verified===true)allowed.youtube_id=entry.youtube_id;
      return {...event,...allowed,rich_content_status:"enriched"};
    });
    const base=all.find(e=>e.event_id===id);
    if(!base)throw new Error("event");
    const key=eventGroupKey(base);
    const occ=all.filter(e=>eventGroupKey(e)===key)
      .sort((a,b)=>(a.start_date+(a.start_time||"99:99")).localeCompare(b.start_date+(b.start_time||"99:99")));
    const e=richEvent(occ);
    const imageEvent=bestImageEvent(occ);

    renderHero(e,occ,imageEvent);
    renderStory(e,occ);
    renderVideo(e);
    renderPeople(e);
    renderSchedule(occ);
    renderPractical(e,occ);
    renderRelated(e,all);
    document.addEventListener("click", action => {
      if (!(action.target instanceof Element)) return;
      const link = action.target.closest("a");
      if (!link) return;
      if (link.matches("#heroBuy, .scheduleBuy")) {
        const row = link.closest(".scheduleItem");
        const selected = row ? occ[Array.from(document.querySelectorAll(".scheduleItem")).indexOf(row)] : e;
        const analytics = window.ashdodAnalytics;
        const params = {...analytics?.metadata(selected),purchase_method:link.protocol === "tel:" ? "phone" : "website"};
        if (row) analytics?.send("select_date",{...analytics.metadata(selected),selected_date:selected.start_date,selection_type:"event_occurrence"});
        analytics?.send("ticket_click",params);
      } else if (link.matches(".relatedCard")) {
        const id = new URL(link.href).searchParams.get("id");
        const selected = all.find(item => item.event_id === id);
        if (selected) window.ashdodAnalytics?.send("select_event",window.ashdodAnalytics.metadata(selected));
      }
    });

    $("loadingState").hidden=true;
    $("page").hidden=false;
  }catch(err){
    $("loadingState").hidden=true;
    $("errorState").hidden=false;
  }
}
init();

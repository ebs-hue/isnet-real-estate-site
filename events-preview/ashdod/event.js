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
function autoStory(e){
  return ["תיאור מפורט של האירוע לא פורסם במקור שבדקנו. המועד, המחיר, המיקום ודרכי יצירת הקשר מופיעים בכרטיס הפרטים. מומלץ לעיין בעמוד האירוע הרשמי לפני הגעה."];
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
    $("heroImage").innerHTML=isRepresentativeHomeGame(e)?sportHeroFallback(e):'<div class="fallback">'+escapeHtml(eventDisplayTitle(e))+'</div>';
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
  const paras=splitParagraphs(e.long_description||e.series_description||e.description);
  const story=paras.length?paras:autoStory(e);
  $("eventStory").innerHTML=story.map(p=>'<p>'+escapeHtml(p)+'</p>').join("");

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
    ["מקום",venues.join(" / ")||"לא פורסם"],
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
  const contact=String(e.contact_phone||e.purchase_phone||"").replace(/[^0-9+]/g,"");
  const contactHtml=contact?'<div class="infoRow"><b>טלפון לבירורים</b><a href="tel:'+escapeHtml(contact)+'">'+escapeHtml(e.contact_phone||e.purchase_phone)+'</a></div>':"";
  const venueAddress=e.address||(e.venue&&e.venue!=="אשדוד"?e.venue:"");
  const maps=venueAddress?'<div class="infoRow"><b>ניווט</b><a href="https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(venueAddress)+'" target="_blank" rel="noopener">לפתיחת מפה ←</a></div>':"";
  const origin=String(e.ticket_url||e.purchase_url||"");
  const source=origin.startsWith("https://")?'<div class="infoRow"><b>מקור רשמי</b><a href="'+escapeHtml(origin)+'" target="_blank" rel="noopener">לעמוד האירוע ←</a></div>':"";
  $("practicalInfo").innerHTML=info+contactHtml+maps+source;
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
    const [data,sports]=await Promise.all([
      fetch("data/events.json?v=20261006-contact-details").then(r=>{if(!r.ok)throw new Error("data");return r.json()}),
      fetch("data/sports.json?v=20261005-2").then(r=>r.json()).catch(()=>({branches:{},teams:[]}))
    ]);
    sportsMeta=sports||{branches:{},teams:[]};
    const all=data.events||[];
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

    $("loadingState").hidden=true;
    $("page").hidden=false;
  }catch(err){
    $("loadingState").hidden=true;
    $("errorState").hidden=false;
  }
}
init();

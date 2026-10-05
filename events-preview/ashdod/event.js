const $=id=>document.getElementById(id);
const catLabels={
  music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים ומשפחה",theatre:"תיאטרון",
  lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",
  festival:"פסטיבלים",community:"קהילה",sport:"ספורט",tour:"סיורים",other:"אירוע"
};
const fmtFull=new Intl.DateTimeFormat("he-IL",{weekday:"long",day:"numeric",month:"long",year:"numeric"});
const fmtMonth=new Intl.DateTimeFormat("he-IL",{month:"short"});
const currency=new Intl.NumberFormat("he-IL",{style:"currency",currency:"ILS",maximumFractionDigits:0});

function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function normalizeSearch(s){
  return String(s||"").toLowerCase()
    .replace(/[״"'׳.,!?():;\/\-–—]/g," ")
    .replace(/\s+/g," ").trim();
}
function localDate(s){const [y,m,d]=String(s||"").split("-").map(Number);return new Date(y,m-1,d)}
function formatTime(t){return t||"השעה תפורסם"}
function priceText(e){
  if(e.is_free===true)return "חינם";
  if(e.price_min_ils==null)return "מחיר לא פורסם";
  if(e.price_max_ils!=null&&e.price_max_ils!==e.price_min_ils)return currency.format(e.price_min_ils)+"–"+currency.format(e.price_max_ils);
  return currency.format(e.price_min_ils);
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
    const k=normalizeSearch(e.title);
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
    sport:"פעילות ספורטיבית",
    tour:"סיור וחוויה בעיר"
  };
  return map[e.category]||"אירוע תרבות ופנאי";
}
function autoPitch(e){
  const where=e.venue?" ב"+e.venue:"";
  return e.title+" באשדוד"+where+" — "+categoryExperience(e)+". כאן תמצאו את כל המועדים, השעות ופרטי ההזמנה במקום אחד.";
}
function autoStory(e){
  const where=e.venue?" ב"+e.venue:"";
  const first='"'+e.title+'" מתקיים באשדוד'+where+'. בעמוד הזה ריכזנו את המידע המעשי שצריך לפני שמחליטים: תאריכים, שעות, מקום, מחיר וקישור ישיר לרכישה כאשר הוא זמין.';
  const byCategory={
    music:"אם אתם מחפשים ערב מוזיקלי בעיר, זה אירוע שכדאי לבדוק מול לוח הזמנים שלכם. המועדים והפרטים המעודכנים מרוכזים כאן כדי לחסוך מעבר בין כמה אתרים.",
    standup:"אם מתחשק לכם ערב של הומור ויציאה מהשגרה, תוכלו לבדוק כאן את המועד הקרוב, מקום המופע ודרך ההזמנה הישירה.",
    kids:"למשפחות שמחפשות פעילות באשדוד, ריכזנו כאן את כל מה שחשוב לתכנון היציאה. מומלץ לבדוק לפני ההזמנה גם את התאמת הגיל כפי שמפורסמת אצל המארגן.",
    theatre:"לחובבי במה ותיאטרון, זה המקום לקבל תמונה מהירה של האירוע ולבחור את המועד שמתאים לכם. כל המידע המעשי מרוכז בעמוד אחד.",
    lecture:"למי שמחפש תוכן, ידע או מפגש מעשיר בעיר, כאן אפשר לראות מתי ואיפה האירוע מתקיים ואיך נרשמים.",
    exhibition:"לחובבי אמנות ותרבות, העמוד מרכז את פרטי הביקור והמידע המעשי הזמין על האירוע.",
    workshop:"למי שמעדיף חוויה פעילה ולא רק צפייה מהצד, כאן מרוכזים פרטי הסדנה, המועדים והמיקום כפי שפורסמו.",
    cinema:"למי שמתכנן יציאה לקולנוע או להקרנה מיוחדת, כאן מרוכזים זמן, מקום ופרטי ההזמנה הזמינים.",
    community:"זהו מפגש קהילתי באשדוד. כאן תוכלו לראות את פרטי המועד והמקום ולבדוק אם נדרשת הרשמה מראש.",
    sport:"למי שמחפש פעילות ספורטיבית בעיר, כאן מרוכזים המועד, המקום ופרטי ההרשמה הזמינים.",
    festival:"למי שמחפש חוויה עירונית רחבה יותר, כאן מרוכזים פרטי האירוע והמועד כדי שתוכלו לתכנן את ההגעה.",
    tour:"למי שרוצה להכיר את העיר דרך סיור או פעילות מודרכת, כאן תוכלו לראות את המועד ופרטי ההצטרפות."
  };
  return [first,byCategory[e.category]||"העמוד מתעדכן לפי המידע הזמין ממקורות האירוע, כך שקל יותר לתכנן יציאה בלי לחפש את הפרטים מחדש."];
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
  document.title=e.title+" | מה עושים באשדוד?";
  const desc=e.short_pitch||e.description||autoPitch(e);
  document.querySelector('meta[name="description"]').setAttribute("content",desc);

  $("heroBadges").innerHTML=
    '<span class="badge accent">'+escapeHtml(catLabels[e.category]||"אירוע")+'</span>'+
    (occ.length>1?'<span class="badge">'+occ.length+' מועדים באשדוד</span>':"");
  $("eventTitle").textContent=e.title;
  $("eventPitch").textContent=e.short_pitch||e.description||autoPitch(e);

  const venues=[...new Set(occ.map(x=>x.venue).filter(Boolean))];
  const dates=[...new Set(occ.map(x=>x.start_date).filter(Boolean))];
  $("heroMeta").innerHTML=[
    venues[0]||"המיקום יפורסם",
    dates.length>1?dates.length+" תאריכים":fmtFull.format(localDate(occ[0].start_date)),
    e.duration_minutes?e.duration_minutes+" דקות":null
  ].filter(Boolean).map(x=>'<span>'+escapeHtml(x)+'</span>').join("");

  if(trustedImage(imageEvent)){
    const src=imageEvent.thumbnail_ready&&imageEvent.thumbnail_url?imageEvent.thumbnail_url:imageEvent.image_url;
    $("heroImage").innerHTML='<img src="'+escapeHtml(src)+'" alt="'+escapeHtml(e.title)+'">';
  }else{
    $("heroImage").innerHTML='<div class="fallback">'+escapeHtml(e.title)+'</div>';
  }

  const action=groupPurchaseAction(occ);
  if(action){
    const a=$("heroBuy");
    a.href=action.href;a.textContent=action.label;a.style.display="inline-flex";
    if(action.kind==="phone")a.removeAttribute("target");else a.target="_blank";
    $("heroBuyNote").hidden=true;
  }else{
    $("heroBuy").style.display="none";
    $("heroBuyNote").hidden=false;
    $("heroBuyNote").textContent="אין כרגע קישור רכישה ישיר מאומת. נוסיף אותו ברגע שנוכל לאמת יעד רכישה ישיר.";
  }
}

function renderStory(e,occ){
  const paras=splitParagraphs(e.long_description||e.description);
  const story=paras.length?paras:autoStory(e);
  $("eventStory").innerHTML=story.map(p=>'<p>'+escapeHtml(p)+'</p>').join("");

  const highlights=Array.isArray(e.highlights)&&e.highlights.length?e.highlights:autoHighlights(e,occ);
  const suitability=e.suitability||autoSuitability(e);
  $("highlightsSection").hidden=false;
  $("highlights").innerHTML=highlights.map(x=>'<div class="highlight">'+escapeHtml(x)+'</div>').join("");
  $("suitability").textContent=suitability;
  $("suitability").hidden=false;
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
        '<span>'+escapeHtml(formatTime(e.start_time))+' · '+escapeHtml(e.venue||"המיקום יפורסם")+'</span>'+
        (own?'<a class="scheduleBuy" href="'+escapeHtml(own.href)+'" '+(own.kind==="url"?'target="_blank" rel="noopener"':'')+'>לפרטים ורכישה ←</a>':"")+
      '</div>'+
    '</div>';
  }).join("");
}

function renderPractical(e,occ){
  const venues=[...new Set(occ.map(x=>x.venue).filter(Boolean))];
  const prices=occ.map(priceText);
  const onePrice=[...new Set(prices)].length===1?prices[0]:"המחיר עשוי להשתנות לפי מועד";
  const audience=(Array.isArray(e.audiences)&&e.audiences.length)?e.audiences.join(", "):null;
  let age=null;
  if(e.age_min!=null&&e.age_max!=null)age="גיל "+e.age_min+"–"+e.age_max;
  else if(e.age_min!=null)age="מגיל "+e.age_min;
  else if(e.age_max!=null)age="עד גיל "+e.age_max;
  const rows=[
    ["מקום",venues.join(" / ")||"יפורסם בהמשך"],
    ["מחיר",onePrice],
    ["משך",e.duration_minutes?e.duration_minutes+" דקות":"לא פורסם"],
    ...(age?[["גילים",age]]:[]),
    ...(audience?[["קהל",audience]]:[]),
    ...(e.organizer?[["מארגן",e.organizer]]:[]),
    ["מספר מועדים",String(occ.length)]
  ];
  $("practicalInfo").innerHTML=rows.map(([a,b])=>'<div class="infoRow"><b>'+escapeHtml(a)+'</b><span>'+escapeHtml(b)+'</span></div>').join("");
}

function renderRelated(current,all){
  const currentKey=normalizeSearch(current.title);
  const related=uniqueByTitle(
    all.filter(e=>normalizeSearch(e.title)!==currentKey&&e.category===current.category)
      .sort((a,b)=>(a.start_date+(a.start_time||"99:99")).localeCompare(b.start_date+(b.start_time||"99:99")))
  ).slice(0,3);

  if(!related.length){$("relatedSection").hidden=true;return}
  $("relatedGrid").innerHTML=related.map(e=>{
    const img=e.thumbnail_ready&&e.thumbnail_url?e.thumbnail_url:(trustedImage(e)?e.image_url:null);
    return '<a class="relatedCard" href="'+directEventUrl(e.event_id)+'">'+
      '<div class="relatedCard__media">'+(img?'<img src="'+escapeHtml(img)+'" alt="">':'')+'</div>'+
      '<div class="relatedCard__body"><h3>'+escapeHtml(e.title)+'</h3><span>'+escapeHtml(fmtFull.format(localDate(e.start_date)))+'</span></div>'+
    '</a>';
  }).join("");
}

async function init(){
  try{
    const id=new URLSearchParams(location.search).get("id");
    if(!id)throw new Error("missing id");
    const data=await fetch("data/events.json?v=20261005-23").then(r=>{
      if(!r.ok)throw new Error("data");
      return r.json();
    });
    const all=data.events||[];
    const base=all.find(e=>e.event_id===id);
    if(!base)throw new Error("event");
    const key=normalizeSearch(base.title);
    const occ=all.filter(e=>normalizeSearch(e.title)===key)
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

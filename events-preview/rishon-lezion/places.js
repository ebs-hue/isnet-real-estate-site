// ISNET shared layout: edit events-preview/ashdod, not this generated file.
const $=id=>document.getElementById(id);
const titles={
  parks:"פארקים בראשון לציון",
  nature:"טבע וטיולים",
  beaches:"החופים בראשון לציון",
  attractions:"אטרקציות",
  culture:"מוסדות תרבות בראשון לציון",
  "must-see":"מקומות שחייבים להכיר"
};
const state={category:new URLSearchParams(location.search).get("category")||"parks",filter:"all",data:null,cat:null};

function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function mapsUrl(q){return "https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(q)}
function setMeta(title,intro){
  document.title=title+" | מה עושים בראשון לציון?";
  const meta=document.querySelector('meta[name="description"]');
  if(meta&&intro)meta.setAttribute("content",intro);
}
function renderHero(cat){
  state.cat=cat;
  $("placesTitle").textContent=cat.title;
  $("placesEyebrow").textContent=cat.eyebrow||"";
  $("placesIntro").textContent=cat.intro||"";
  $("heroBackdrop").style.backgroundImage='url("'+String(cat.hero_image||"").replace(/"/g,"%22")+'")';
  $("heroCredit").textContent=cat.hero_credit||"";
  $("placesStats").innerHTML=(cat.stats||[]).map(x=>
    '<div class="stat"><b>'+esc(x.value)+'</b><span>'+esc(x.label)+'</span></div>'
  ).join("");
  setMeta(cat.title,cat.intro);
}
function placeCard(item){
  const tags=(item.badges||[]).map(x=>'<span>'+esc(x)+'</span>').join("");
  const highlights=(item.highlights||[]).map(x=>'<li>'+esc(x)+'</li>').join("");
  return '<article class="placeCard">'+
    '<div class="placeMedia">'+
      '<img src="'+esc(item.image)+'" alt="'+esc(item.name)+'" loading="lazy" onerror="this.closest(\'.placeMedia\').classList.add(\'imageFailed\');this.remove()">'+
      '<div class="placeBadges">'+tags+'</div>'+
      (item.image_credit?'<small class="imageCredit">'+esc(item.image_credit)+'</small>':'')+
    '</div>'+
    '<div class="placeBody">'+
      '<span class="placeType">'+esc(state.cat?.item_label||(state.category==="beaches"?"חוף בראשון לציון":"מקום בראשון לציון"))+'</span>'+
      '<h2>'+esc(item.name)+'</h2>'+
      '<h3>'+esc(item.tagline||"")+'</h3>'+
      '<p>'+esc(item.description||"")+'</p>'+
      '<ul class="placeHighlights">'+highlights+'</ul>'+
      '<div class="placeActions">'+
        '<a class="primaryAction" href="'+mapsUrl(item.map_query||item.name+" ראשון לציון")+'" target="_blank" rel="noopener">איך מגיעים ←</a>'+
      '</div>'+
    '</div>'+
  '</article>';
}
function renderFilters(cat){
  const wrap=$("placeFilters");
  const heading=$("placesFilterTitle");
  if(heading)heading.textContent=cat.filter_title||"מה מתאים לכם?";
  wrap.innerHTML=(cat.filters||[]).map(f=>
    '<button class="'+(state.filter===f.id?"is-active":"")+'" data-filter="'+esc(f.id)+'">'+esc(f.label)+'</button>'
  ).join("");
  $("placesToolbar").hidden=false;
  wrap.onclick=e=>{
    const b=e.target.closest("[data-filter]");if(!b)return;
    state.filter=b.dataset.filter;
    renderGrid(cat);
    renderFilters(cat);
  };
}
function renderGrid(cat){
  const arr=(cat.items||[]).filter(x=>state.filter==="all"||(x.tags||[]).includes(state.filter));
  $("placesGrid").innerHTML=arr.length
    ?arr.map(placeCard).join("")
    :'<div class="emptyPlaces"><b>לא מצאנו מקום בסינון הזה</b><span>בחרו אפשרות אחרת.</span></div>';
}
function renderSafety(cat){
  if(!cat.safety_title&&!cat.safety_text)return;
  $("safetyTitle").textContent=cat.safety_title||"";
  $("safetyText").textContent=cat.safety_text||"";
  const official=$("officialStatusLink"),tourism=$("tourismSourceLink");
  if(cat.official_status_url)official.href=cat.official_status_url;else official.hidden=true;
  if(cat.tourism_source_url)tourism.href=cat.tourism_source_url;else tourism.hidden=true;
  $("safetyCard").hidden=false;
}
function renderBeachInfo(cat){
  if(state.category!=="beaches")return;
  const info=$("beachInfo"); if(!info)return;

  if(cat.season){
    $("seasonCard").innerHTML=
      '<span class="infoPanel__label">עונת הרחצה</span>'+
      '<h2>'+esc(cat.season.title||"")+'</h2>'+
      '<div class="seasonDates"><b>'+esc(cat.season.start||"")+'</b><span>עד</span><b>'+esc(cat.season.end||"")+'</b></div>'+
      '<strong class="seasonHours">'+esc(cat.season.current_hours||"")+'</strong>'+
      '<p>'+esc(cat.season.note||"")+'</p>'+
      (cat.season.source_url?'<a href="'+esc(cat.season.source_url)+'" target="_blank" rel="noopener">לשעות הרשמיות ←</a>':'');
  }

  if(cat.environment){
    $("environmentCard").innerHTML=
      '<span class="infoPanel__label">'+esc(cat.environment.badge||"")+'</span>'+
      '<h2>'+esc(cat.environment.title||"")+'</h2>'+
      '<p>'+esc(cat.environment.text||"")+'</p>'+
      (cat.environment.source_url?'<a href="'+esc(cat.environment.source_url)+'" target="_blank" rel="noopener">למידע העירוני ←</a>':'');
  }

  if(cat.daily_status){
    $("dailyStatusCard").innerHTML=
      '<span class="infoPanel__label">מצב הים</span>'+
      '<h2>'+esc(cat.daily_status.title||"")+'</h2>'+
      '<p>'+esc(cat.daily_status.text||"")+'</p>'+
      (cat.daily_status.source_url?'<a href="'+esc(cat.daily_status.source_url)+'" target="_blank" rel="noopener">מצב החופים בראשון נט ←</a>':'');
  }

  $("beachRules").innerHTML=(cat.rules||[]).map((rule,i)=>
    '<div class="beachRule"><span>'+(i+1)+'</span><p>'+esc(rule)+'</p></div>'
  ).join("");

  info.hidden=false;
}
function renderComingSoon(){
  const title=titles[state.category]||"מה עושים בראשון לציון?";
  $("placesHero").hidden=true;
  $("placesToolbar").hidden=true;
  $("placesPanel").hidden=true;
  $("safetyCard").hidden=true;
  $("comingSoonTitle").textContent=title;
  $("comingSoon").hidden=false;
  document.title=title+" | מה עושים בראשון לציון?";
}
async function init(){
  try{
    const data=await fetch("data/places.json?ts="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("places data");return r.json()});
    state.data=data;
    const cat=data.categories?.[state.category];
    if(!cat){renderComingSoon();return}
    renderHero(cat);
    renderFilters(cat);
    renderGrid(cat);
    renderBeachInfo(cat);
    renderSafety(cat);
    $("placesPanel").hidden=false;
  }catch(err){
    console.error(err);
    renderComingSoon();
  }
}
init();
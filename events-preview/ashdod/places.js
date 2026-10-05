const $=id=>document.getElementById(id);
const titles={
  parks:"פארקים באשדוד",
  nature:"טבע וטיולים",
  beaches:"החופים באשדוד",
  attractions:"אטרקציות",
  culture:"מוסדות תרבות באשדוד",
  "must-see":"מקומות שחייבים להכיר"
};
const state={category:new URLSearchParams(location.search).get("category")||"parks",filter:"all",data:null};

function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function mapsUrl(q){return "https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(q)}
function setMeta(title,intro){
  document.title=title+" | מה עושים באשדוד?";
  const meta=document.querySelector('meta[name="description"]');
  if(meta&&intro)meta.setAttribute("content",intro);
}
function renderHero(cat){
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
      '<span class="placeType">'+(state.category==="beaches"?"חוף באשדוד":"מקום באשדוד")+'</span>'+
      '<h2>'+esc(item.name)+'</h2>'+
      '<h3>'+esc(item.tagline||"")+'</h3>'+
      '<p>'+esc(item.description||"")+'</p>'+
      '<ul class="placeHighlights">'+highlights+'</ul>'+
      '<div class="placeActions">'+
        '<a class="primaryAction" href="'+mapsUrl(item.map_query||item.name+" אשדוד")+'" target="_blank" rel="noopener">איך מגיעים ←</a>'+
        (item.source_url?'<a class="sourceAction" href="'+esc(item.source_url)+'" target="_blank" rel="noopener">מידע נוסף</a>':'')+
      '</div>'+
    '</div>'+
  '</article>';
}
function renderFilters(cat){
  const wrap=$("placeFilters");
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
function renderComingSoon(){
  const title=titles[state.category]||"מה עושים באשדוד?";
  $("placesHero").hidden=true;
  $("placesToolbar").hidden=true;
  $("placesPanel").hidden=true;
  $("safetyCard").hidden=true;
  $("comingSoonTitle").textContent=title;
  $("comingSoon").hidden=false;
  document.title=title+" | מה עושים באשדוד?";
}
async function init(){
  try{
    const data=await fetch("data/places.json?v=20261005-1").then(r=>{if(!r.ok)throw new Error("places data");return r.json()});
    state.data=data;
    const cat=data.categories?.[state.category];
    if(!cat){renderComingSoon();return}
    renderHero(cat);
    renderFilters(cat);
    renderGrid(cat);
    renderSafety(cat);
    $("placesPanel").hidden=false;
  }catch(err){
    console.error(err);
    renderComingSoon();
  }
}
init();
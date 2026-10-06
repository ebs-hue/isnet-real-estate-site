// ISNET shared layout: edit events-preview/ashdod, not this generated file.
const state={movies:[],venue:"all",audience:"all",query:"",updatedAt:null};
const $=id=>document.getElementById(id);
const fmtDate=new Intl.DateTimeFormat("he-IL",{weekday:"short",day:"numeric",month:"short"});
function esc(v){return String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function todayIso(){const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,"0"),String(d.getDate()).padStart(2,"0")].join("-")}
function localDate(s){const [y,m,d]=String(s).split("-").map(Number);return new Date(y,m-1,d)}
function venueShort(v){return v.id==="cinema-city"?"סינמה סיטי":v.name}
function nextSchedule(v){
  const day=todayIso(), schedule=v.schedule||{};
  if(Array.isArray(schedule[day])&&schedule[day].length)return {date:day,label:"היום",times:schedule[day]};
  const next=Object.keys(schedule).filter(d=>d>=day).sort()[0];
  return next?{date:next,label:fmtDate.format(localDate(next)),times:schedule[next]||[]}:{date:null,label:"השעות יתעדכנו",times:[]};
}
function matches(m){
  if(state.audience==="family"&&!m.is_family)return false;
  if(state.venue!=="all"&&!m.venues.some(v=>v.id===state.venue))return false;
  const q=state.query.trim().toLowerCase();
  if(!q)return true;
  return [m.title,m.synopsis,...m.venues.map(v=>v.name)].join(" ").toLowerCase().includes(q);
}
function card(m){
  const venues=m.venues.filter(v=>state.venue==="all"||v.id===state.venue);
  const image=m.trailer_youtube_id?"https://i.ytimg.com/vi/"+encodeURIComponent(m.trailer_youtube_id)+"/hqdefault.jpg":"";
  const schedule=venues.map(v=>{
    const s=nextSchedule(v);
    const times=s.times.slice(0,8).map(t=>'<span class="showTime">'+esc(t)+'</span>').join("");
    return '<div class="venueRow"><div class="venueName"><b>'+esc(venueShort(v))+'</b><span>'+esc(s.label)+'</span></div><div class="showTimes">'+(times||'<span class="noTimes">בדקו שעות בעמוד הסרט</span>')+'</div></div>';
  }).join("");
  return '<article class="movieCard">'+
    '<button class="moviePoster" type="button" data-trailer="'+esc(m.id)+'" '+(!m.trailer_youtube_id?'disabled':'')+'>'+
      (image?'<img src="'+image+'" alt="" loading="lazy">':'<div class="posterFallback">🎬</div>')+
      (m.trailer_youtube_id?'<span class="playBadge"><i>▶</i><b>צפו בטריילר</b></span>':'')+
    '</button>'+
    '<div class="movieBody">'+
      '<div class="movieBadges">'+(m.is_family?'<span class="family">ילדים ומשפחה</span>':'')+venues.map(v=>'<span>'+esc(venueShort(v))+'</span>').join("")+'</div>'+
      '<h3><a href="movie.html?id='+encodeURIComponent(m.id)+'">'+esc(m.title)+'</a></h3>'+
      '<p>'+esc(m.synopsis||"")+'</p>'+
      '<div class="scheduleBox">'+schedule+'</div>'+
      '<a class="movieDetails" href="movie.html?id='+encodeURIComponent(m.id)+'">כל הימים והשעות ←</a>'+
    '</div>'+
  '</article>';
}
function render(){
  const arr=state.movies.filter(matches).sort((a,b)=>a.title.localeCompare(b.title,"he"));
  $("cinemaGrid").innerHTML=arr.map(card).join("");
  $("emptyState").hidden=arr.length>0;
  $("resultsMeta").textContent=arr.length+" סרטים";
  document.querySelectorAll("[data-trailer]").forEach(b=>b.onclick=()=>openTrailer(b.dataset.trailer));
  document.querySelectorAll("[data-audience]").forEach(b=>b.classList.toggle("is-active",b.dataset.audience===state.audience));
  document.querySelectorAll("[data-venue]").forEach(b=>b.classList.toggle("is-active",b.dataset.venue===state.venue));
}
function openTrailer(id){
  const m=state.movies.find(x=>x.id===id);if(!m||!m.trailer_youtube_id)return;
  $("trailerTitle").textContent=m.title;
  $("trailerSynopsis").textContent=m.synopsis||"";
  $("trailerFrame").src="https://www.youtube-nocookie.com/embed/"+encodeURIComponent(m.trailer_youtube_id)+"?autoplay=1&rel=0";
  $("trailerFrame").title="טריילר - "+m.title;
  $("trailerDetails").href="movie.html?id="+encodeURIComponent(m.id);
  $("trailerModal").hidden=false;
  document.body.style.overflow="hidden";
}
function closeTrailer(){
  $("trailerModal").hidden=true;$("trailerFrame").src="";document.body.style.overflow="";
}
async function init(){
  const data=await fetch("data/cinema.json",{cache:"no-store"}).then(r=>r.json());
  state.movies=data.movies||[];state.updatedAt=data.updated_at||null;
  if(state.updatedAt){const d=new Date(state.updatedAt);if(!Number.isNaN(d.getTime()))$("cinemaUpdated").textContent="עודכן "+new Intl.DateTimeFormat("he-IL",{day:"numeric",month:"numeric",hour:"2-digit",minute:"2-digit"}).format(d)}
  document.querySelectorAll("[data-audience]").forEach(b=>b.onclick=()=>{state.audience=b.dataset.audience;render()});
  document.querySelectorAll("[data-venue]").forEach(b=>b.onclick=()=>{state.venue=b.dataset.venue;render()});
  $("movieSearch").oninput=e=>{state.query=e.target.value;render()};
  document.querySelectorAll("[data-close-trailer]").forEach(b=>b.onclick=closeTrailer);
  document.addEventListener("keydown",e=>{if(e.key==="Escape")closeTrailer()});
  render();
}
init().catch(err=>{console.error(err);$("emptyState").hidden=false;$("emptyState").innerHTML="<h3>לא הצלחנו לטעון את הסרטים</h3><p>נסו לרענן את העמוד.</p>"});

// ISNET shared layout: edit events-preview/ashdod, not this generated file.
const $=id=>document.getElementById(id);
const fmtFull=new Intl.DateTimeFormat("he-IL",{weekday:"long",day:"numeric",month:"long",year:"numeric"});
const fmtShort=new Intl.DateTimeFormat("he-IL",{weekday:"short",day:"numeric",month:"short"});
function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
function localDate(s){const [y,m,d]=String(s||"").split("-").map(Number);return new Date(y,m-1,d)}
function movieUrl(id){return "movie.html?id="+encodeURIComponent(id)}
function venueLabel(id){return id==="cinema-city"?"סינמה סיטי ראשון לציון":"פלאנט ראשון לציון"}
function allDates(movie){
  const dates=new Set();
  movie.venues.forEach(v=>Object.keys(v.schedule||{}).forEach(d=>dates.add(d)));
  return [...dates].sort();
}
function renderHero(movie){
  document.title=movie.title+" | מה עושים בראשון לציון?";
  document.querySelector('meta[name="description"]').setAttribute("content",movie.synopsis||"כל שעות ההקרנה והפרטים על הסרט בראשון לציון.");
  $("movieTitle").textContent=movie.title;
  $("movieSynopsis").textContent=movie.synopsis||"כל הימים, השעות ובתי הקולנוע בראשון לציון במקום אחד.";
  const badges=[];
  if(movie.is_family)badges.push('<span class="badge family">ילדים ומשפחה</span>');
  movie.venues.forEach(v=>badges.push('<span class="badge">'+escapeHtml(v.name)+'</span>'));
  $("heroBadges").innerHTML=badges.join("");
  const dates=allDates(movie);
  $("heroMeta").innerHTML=[
    movie.venues.length===2?"מוצג בשני בתי קולנוע":movie.venues[0]?.name,
    dates.length?dates.length+" ימי הקרנה מעודכנים":"השעות מתעדכנות",
    movie.trailer_youtube_id?"טריילר זמין":null
  ].filter(Boolean).map(x=>'<span>'+escapeHtml(x)+'</span>').join("");
  if(movie.trailer_youtube_id){
    const img="https://i.ytimg.com/vi/"+encodeURIComponent(movie.trailer_youtube_id)+"/hqdefault.jpg";
    $("heroMedia").innerHTML='<button id="heroMediaTrailer" class="heroPoster" type="button"><img src="'+img+'" alt=""><span><i>▶</i><b>צפו בטריילר</b></span></button>';
    $("heroTrailer").hidden=false;
    $("heroTrailer").onclick=()=>document.getElementById("trailerSection")?.scrollIntoView({behavior:"smooth",block:"start"});
    $("heroMediaTrailer").onclick=()=>document.getElementById("trailerSection")?.scrollIntoView({behavior:"smooth",block:"start"});
  }else{
    $("heroMedia").innerHTML='<div class="heroFallback"><span>🎬</span><b>'+escapeHtml(movie.title)+'</b></div>';
    $("heroTrailer").hidden=true;
  }
}
function renderSchedules(movie){
  $("cinemaSchedules").innerHTML=movie.venues.map(v=>{
    const dates=Object.keys(v.schedule||{}).sort();
    const rows=dates.length?dates.map(date=>{
      const times=(v.schedule[date]||[]).map(t=>'<span class="showtime">'+escapeHtml(t)+'</span>').join("");
      return '<div class="dayRow">'+
        '<div class="dayDate"><b>'+escapeHtml(fmtShort.format(localDate(date)))+'</b><span>'+escapeHtml(date.split("-").reverse().join("."))+'</span></div>'+
        '<div class="dayTimes">'+times+'</div>'+
      '</div>';
    }).join(""):'<div class="noSchedule">השעות המדויקות טרם פורסמו אצלנו. הן ייכנסו אוטומטית בעדכון הקרוב.</div>';
    return '<section class="cinemaBlock">'+
      '<div class="cinemaBlock__head"><div><span>בית קולנוע</span><h3>'+escapeHtml(v.name)+'</h3></div>'+
      '<span class="screeningCount">'+dates.length+' ימים</span></div>'+
      '<div class="daysList">'+rows+'</div>'+
    '</section>';
  }).join("");
}
function renderTrailer(movie){
  if(!movie.trailer_youtube_id){$("trailerSection").hidden=true;return}
  $("trailerSection").hidden=false;
  $("youtubeFrame").src="https://www.youtube-nocookie.com/embed/"+encodeURIComponent(movie.trailer_youtube_id)+"?rel=0";
  $("youtubeFrame").title="טריילר - "+movie.title;
}
function renderSources(movie,updatedAt){
  $("sourceLinks").innerHTML=movie.venues.map(v=>
    '<a href="'+escapeHtml(v.article_url)+'" target="_blank" rel="noopener"><b>'+escapeHtml(v.name)+'</b><span>מקור הנתונים בראשון נט ↗</span></a>'
  ).join("");
  if(updatedAt){
    const d=new Date(updatedAt);
    if(!Number.isNaN(d.getTime()))$("updatedAt").textContent="הנתונים עודכנו "+new Intl.DateTimeFormat("he-IL",{day:"numeric",month:"numeric",year:"numeric",hour:"2-digit",minute:"2-digit"}).format(d);
  }
}
function renderRelated(movie,all){
  let related=all.filter(m=>m.id!==movie.id);
  related.sort((a,b)=>{
    const af=Boolean(a.is_family)===Boolean(movie.is_family)?0:1;
    const bf=Boolean(b.is_family)===Boolean(movie.is_family)?0:1;
    return af-bf||a.title.localeCompare(b.title,"he");
  });
  $("relatedGrid").innerHTML=related.slice(0,4).map(m=>{
    const img=m.trailer_youtube_id?"https://i.ytimg.com/vi/"+encodeURIComponent(m.trailer_youtube_id)+"/hqdefault.jpg":"";
    return '<a class="relatedCard" href="'+movieUrl(m.id)+'">'+
      '<div class="relatedCard__media">'+(img?'<img src="'+img+'" alt="">':'<div class="relatedFallback">🎬</div>')+'</div>'+
      '<div class="relatedCard__body">'+(m.is_family?'<span class="miniBadge">ילדים ומשפחה</span>':'')+'<h3>'+escapeHtml(m.title)+'</h3><span>'+escapeHtml(m.venues.map(v=>v.id==="cinema-city"?"סינמה סיטי":"פלאנט").join(" · "))+'</span></div>'+
    '</a>';
  }).join("");
}
async function init(){
  try{
    const id=new URLSearchParams(location.search).get("id");
    if(!id)throw new Error("missing id");
    const data=await fetch("data/cinema.json?v=20261005-4").then(r=>{if(!r.ok)throw new Error("data");return r.json()});
    const movie=(data.movies||[]).find(m=>m.id===id);
    if(!movie)throw new Error("movie");
    renderHero(movie);
    renderSchedules(movie);
    renderTrailer(movie);
    $("fullSynopsis").textContent=movie.synopsis||"פרטי הסרט יתעדכנו כאן.";
    renderSources(movie,data.updated_at);
    renderRelated(movie,data.movies||[]);
    $("loadingState").hidden=true;
    $("page").hidden=false;
  }catch(err){
    console.error(err);
    $("loadingState").hidden=true;
    $("errorState").hidden=false;
  }
}
init();
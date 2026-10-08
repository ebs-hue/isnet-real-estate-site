const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const cities=[{slug:"ashdod",name:"אשדוד",base:"../ashdod/"},{slug:"rishon-lezion",name:"ראשון לציון",base:"../rishon-lezion/"}];
let rows=[];
function imgUrl(e){
 const u=e.thumbnail_url||e.image_url||"";
 if(!u)return "";
 return /^(https?:|data:)/.test(u)?u:e._base+u;
}
function status(e){
 const has=Boolean(e.thumbnail_url||e.image_url);
 if(!has)return"missing";
 return e.image_verified===true&&e.image_publishable===true?"approved":"review";
}
function enriched(e){
 return Boolean(e.content_enrichment_version||e.event_summary||e.image_brief||e.short_pitch||e.long_description);
}
function hay(e){return [e.title,e.event_summary,e.short_pitch,e.long_description,e.image_brief,e.artist_name,e.production_name,...(Array.isArray(e.participants)?e.participants:[])].filter(Boolean).join(" ").toLowerCase()}
async function load(){
 const groups=await Promise.all(cities.map(async c=>{
  const d=await fetch(c.base+"data/events.json",{cache:"no-store"}).then(r=>r.json());
  return (d.events||[]).filter(e=>e.start_date>=new Date().toISOString().slice(0,10)).map(e=>({...e,_city:c.slug,_cityName:c.name,_base:c.base}));
 }));
 rows=groups.flat(); render();
}
function filtered(){
 const q=$("qaQ").value.trim().toLowerCase(),city=$("qaCity").value,st=$("qaStatus").value,ct=$("qaContent").value;
 return rows.filter(e=>{
  if(q&&!hay(e).includes(q))return false;
  if(city&&e._city!==city)return false;
  if(st&&status(e)!==st)return false;
  if(ct==="enriched"&&!enriched(e))return false;
  if(ct==="ready"&&e.content_ready_for_media!==true)return false;
  return true;
 }).sort((a,b)=>(a.start_date||"").localeCompare(b.start_date||""));
}
function renderStats(){
 const future=rows.length, en=rows.filter(enriched).length, approved=rows.filter(e=>status(e)==="approved").length, review=rows.filter(e=>status(e)==="review").length, missing=rows.filter(e=>status(e)==="missing").length;
 $("qaStats").innerHTML=[[future,"אירועים עתידיים"],[en,"עברו העשרת תוכן"],[approved,"תמונה מאושרת"],[review,"תמונה לבדיקה"],[missing,"ללא תמונה"]].map(([n,t])=>'<article class="stat"><strong>'+n+'</strong><span>'+t+'</span></article>').join("");
}
function render(){
 renderStats(); const xs=filtered();
 $("qaCount").textContent=xs.length+" אירועים מוצגים";
 $("qaEmpty").hidden=xs.length>0;
 $("qaGrid").innerHTML=xs.slice(0,500).map(e=>{
  const im=imgUrl(e),st=status(e),lab=st==="approved"?"מאושרת":st==="review"?"לבדיקה":"חסרה",cls=st==="approved"?"good":st==="review"?"warn":"bad";
  const summary=e.event_summary||e.short_pitch||e.long_description||e.description||"אין עדיין תקציר.";
  const brief=e.image_brief||"לא נוצר עדיין בריף תמונה.";
  const people=Array.isArray(e.participants)?e.participants.join(" · "):(e.participants||e.artist_name||"");
  return '<article class="qa-card">'+
   '<div class="qa-image">'+(im?'<img loading="lazy" src="'+esc(im)+'" alt="">':'<div class="media-img-placeholder">אין תמונה</div>')+'<span class="tag '+cls+' media-badge">'+lab+'</span></div>'+
   '<div class="qa-body"><div class="qa-head"><div><h3>'+esc(e.title||"")+'</h3><small>'+esc(e._cityName)+' · '+esc(e.start_date||"")+'</small></div></div>'+
   (people?'<div class="qa-line"><strong>אמן/משתתפים:</strong> '+esc(people)+'</div>':'')+
   '<div class="qa-block"><strong>מה האירוע:</strong><p>'+esc(summary)+'</p></div>'+
   '<div class="qa-block brief"><strong>בריף לעורך התמונות:</strong><p>'+esc(brief)+'</p></div>'+
   '<div class="qa-foot"><span>'+esc(e.image_strategy||"ללא אסטרטגיית תמונה")+'</span><span>'+esc(e.image_rights_status||"זכויות לא מסומנות")+'</span></div>'+
  '</div></article>';
 }).join("");
}
["qaQ","qaCity","qaStatus","qaContent"].forEach(id=>$(id).addEventListener("input",render));
$("qaClear").addEventListener("click",()=>{$("qaQ").value="";$("qaCity").value="";$("qaStatus").value="";$("qaContent").value="enriched";render()});
load().catch(e=>{$("qaCount").textContent="שגיאה בטעינת הנתונים";console.error(e)});

const TODAY=new Date().toISOString().slice(0,10);
const CITIES=[["ashdod","אשדוד"],["rishon-lezion","ראשון לציון"]];
const LABELS={music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים",theatre:"תיאטרון",lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה",sport:"ספורט",tour:"סיורים",other:"אחר"};
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let items=[];
function mediaImage(event,media){
  if(media?.card_url)return "../"+media.card_url;
  const u=event.thumbnail_url||event.image_url||"";
  if(/^(https?:|data:)/.test(u))return u;
  return u?("../"+event._city+"/"+u):"";
}
function textReady(e){return Boolean(e.content_ready_for_media===true || e.content_enrichment_version || e.event_summary || e.image_brief || e.long_description || e.short_pitch)}
function eventText(e){return e.event_summary||e.short_pitch||e.long_description||e.description||e.series_description||""}
function imageState(e,m){
  if(!(e.thumbnail_url||e.image_url))return "missing";
  if(m?.status==="approved" || (e.image_verified===true&&e.image_publishable===true))return "approved";
  return "review";
}
async function load(){
  const bank=await fetch("../media-bank/data/media.json",{cache:"no-store"}).then(r=>r.json()).catch(()=>({media:[]}));
  const byOrigin=new Map();
  for(const m of bank.media||[]){
    for(const ev of m.events||[])byOrigin.set(ev.city+":"+ev.event_id,m);
  }
  const data=await Promise.all(CITIES.map(async ([slug,name])=>{
    const d=await fetch("../"+slug+"/data/events.json",{cache:"no-store"}).then(r=>r.json());
    return (d.events||[]).filter(e=>String(e.start_date||"")>=TODAY && textReady(e)).map(e=>({...e,_city:slug,_cityName:name,_media:byOrigin.get(slug+":"+e.event_id)||null}));
  }));
  items=data.flat();
  $("qaCity").innerHTML='<option value="">כל הערים</option>'+CITIES.map(([s,n])=>'<option value="'+s+'">'+n+'</option>').join("");
  render();
}
function filtered(){
  const q=$("qaQ").value.trim().toLowerCase(),city=$("qaCity").value,img=$("qaImage").value,reuse=$("qaReuse").value;
  return items.filter(e=>{
    const state=imageState(e,e._media);
    if(city&&e._city!==city)return false;
    if(img&&state!==img)return false;
    if(reuse&&(e._media?.reuse_risk||"low")!==reuse)return false;
    if(q){
      const hay=[e.title,eventText(e),e.image_brief,e.artist_name,e.production_name,e.category,...(Array.isArray(e.participants)?e.participants:[])].filter(Boolean).join(" ").toLowerCase();
      if(!hay.includes(q))return false;
    }
    return true;
  });
}
function render(){
  const rows=filtered();
  const approved=items.filter(e=>imageState(e,e._media)==="approved").length;
  const review=items.filter(e=>imageState(e,e._media)==="review").length;
  const missing=items.filter(e=>imageState(e,e._media)==="missing").length;
  const suspicious=items.filter(e=>e._media?.reuse_risk==="review").length;
  $("qaStats").innerHTML=[
    [items.length,"אירועים עם תוכן","עתידיים שעברו העשרה"],
    [approved,"תמונה מאושרת","מקור/זכויות לפי המידע הקיים"],
    [review,"תמונה לבדיקה","דורשת בקרה"],
    [missing,"ללא תמונה","עורך התמונות צריך לטפל"],
    [suspicious,"שימוש חוזר חשוד","אותה תמונה באירועים שונים"]
  ].map(([n,t,d])=>'<article class="stat"><strong>'+n+'</strong><span>'+t+'</span><small>'+d+'</small></article>').join("");
  $("qaCount").textContent=rows.length+" אירועים מוצגים מתוך "+items.length;
  $("qaEmpty").hidden=rows.length>0;
  $("qaGrid").innerHTML=rows.slice(0,500).map(e=>{
    const m=e._media,state=imageState(e,m),img=mediaImage(e,m);
    const badge=state==="approved"?"good":state==="missing"?"bad":"warn";
    const stateText=state==="approved"?"מאושרת":state==="missing"?"חסרה":"לבדיקה";
    const brief=e.image_brief||"לא נוצר עדיין בריף תמונה";
    const summary=eventText(e)||"אין תקציר";
    const source=m?.source_url||e.image_source||e.image_origin_url||"—";
    return '<article class="qa-card">'+
      '<div class="qa-image">'+(img?'<img loading="lazy" src="'+esc(img)+'" alt="">':'<div class="media-img-placeholder">אין תמונה</div>')+
      '<span class="tag '+badge+' media-badge">'+stateText+'</span></div>'+
      '<div class="qa-body"><div class="qa-head"><div><h3>'+esc(e.title||"")+'</h3><p>'+esc(e._cityName)+' · '+esc(LABELS[e.category]||e.category||"")+' · '+esc(e.start_date||"")+'</p></div></div>'+
      '<section><strong>מה סוכן התוכן הבין</strong><p>'+esc(summary)+'</p></section>'+
      '<section><strong>בריף לעורך התמונות</strong><p>'+esc(brief)+'</p></section>'+
      '<div class="qa-meta"><span>שיטה: '+esc(m?.strategy||e.image_strategy||"—")+'</span><span>שימושים: '+esc(m?.usage_count||1)+'</span>'+
      (m?.reuse_risk==="review"?'<span class="tag bad">שימוש חוזר חשוד</span>':'')+'</div>'+
      '<small class="qa-source" title="'+esc(source)+'">מקור: '+esc(source)+'</small>'+
      '</div></article>';
  }).join("");
}
["qaQ","qaCity","qaImage","qaReuse"].forEach(id=>$(id).addEventListener("input",render));
$("qaClear").addEventListener("click",()=>{["qaQ","qaCity","qaImage","qaReuse"].forEach(id=>$(id).value="");render()});
load().catch(err=>{$("qaCount").textContent="שגיאה בטעינת בקרת התמונות";console.error(err)});

const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const CAT={music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים",theatre:"תיאטרון",lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה",sport:"ספורט",tour:"סיורים",other:"אחר"};
let data={artists:[],productions:[],media:[]}, mediaById=new Map();
function cardUrl(m){
 if(!m)return "";
 if(m.card_url)return "../"+String(m.card_url).replace(/^\/+|^media-bank\//g,"media-bank/");
 const u=m.thumbnail_url||m.url||"";
 if(/^(https?:|data:|\/)/.test(u))return u;
 const city=(m.cities||[])[0];
 return city?"../"+city+"/"+u:u;
}
function current(){
 const type=$("entityType").value, q=$("entityQ").value.trim().toLowerCase(), reuse=$("entityReusable").value;
 let xs=type==="artist"?data.artists:data.productions;
 return xs.filter(x=>{
  const name=x.name||x.label||"";
  if(q&&!name.toLowerCase().includes(q))return false;
  const has=Boolean(x.preferred_media_id);
  if(reuse==="yes"&&!has)return false;if(reuse==="no"&&has)return false;
  return true;
 }).sort((a,b)=>(Boolean(b.preferred_media_id)-Boolean(a.preferred_media_id))||String(a.name||a.label).localeCompare(String(b.name||b.label),"he"));
}
function renderStats(){
 $("entityStats").innerHTML=[
  [data.artists.length,"אמנים מוכרים","ברשת כולה"],
  [data.artists.filter(x=>x.preferred_media_id).length,"אמנים עם תמונה","מוכנה לשימוש חוזר"],
  [data.productions.length,"מופעים והפקות","מזוהים בבנק"],
  [data.productions.filter(x=>x.preferred_media_id).length,"מופעים עם תמונה","מוכנה לשימוש חוזר"],
  [data.media.filter(x=>x.status==="approved").length,"תמונות מאושרות","בבנק המרכזי"]
 ].map(([n,t,s])=>'<article class="stat"><strong>'+n+'</strong><span>'+t+'</span><small>'+s+'</small></article>').join("");
}
function render(){
 renderStats();const type=$("entityType").value,xs=current();
 $("entityTitle").textContent=type==="artist"?"אמנים":"מופעים והפקות";
 $("entityCount").textContent=xs.length+" פרופילים מוצגים";
 $("entityEmpty").hidden=xs.length>0;
 $("entityGrid").innerHTML=xs.slice(0,600).map(x=>{
  const m=mediaById.get(x.preferred_media_id),img=cardUrl(m);
  const name=x.name||x.label||"";
  const cats=(x.categories||[]).map(c=>CAT[c]||c).join(" · ");
  const cities=(x.cities||[]).map(c=>c==="ashdod"?"אשדוד":c==="rishon-lezion"?"ראשון לציון":c).join(" · ");
  return '<article class="entity-card">'+
    '<div class="entity-image">'+(img?'<img loading="lazy" src="'+esc(img)+'" alt="">':'<div class="media-img-placeholder">אין עדיין תמונה מאושרת</div>')+
    (m?'<span class="tag good media-badge">מוכנה לשימוש חוזר</span>':'<span class="tag warn media-badge">דרושה תמונה</span>')+'</div>'+
    '<div class="entity-body"><h3>'+esc(name)+'</h3>'+
    '<div class="media-meta">'+(cats?'<span>'+esc(cats)+'</span>':'')+(cities?'<span>'+esc(cities)+'</span>':'')+
    '<span>'+esc(String(x.approved_media_count||0))+' תמונות מאושרות</span></div>'+
    (m?'<small>'+esc(m.credit||m.rights_status||"מקור מאושר")+'</small>':'<small>בפעם הבאה שהשם יופיע, סוכן האיסוף יחפש תמונת מקור.</small>')+
    '</div></article>';
 }).join("");
}
async function load(){
 const [a,p,m]=await Promise.all([
  fetch("../media-bank/data/artists.json",{cache:"no-store"}).then(r=>r.json()),
  fetch("../media-bank/data/productions.json",{cache:"no-store"}).then(r=>r.json()),
  fetch("../media-bank/data/media.json",{cache:"no-store"}).then(r=>r.json())
 ]);
 data={artists:a.artists||[],productions:p.productions||[],media:m.media||[]};
 mediaById=new Map(data.media.map(x=>[x.media_id,x]));
 render();
}
["entityQ","entityType","entityReusable"].forEach(id=>$(id).addEventListener("input",render));
load().catch(err=>{$("entityCount").textContent="שגיאה בטעינת המאגר";console.error(err)});

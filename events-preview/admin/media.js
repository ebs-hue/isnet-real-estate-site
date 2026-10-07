const LABELS={music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים",theatre:"תיאטרון",lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה",sport:"ספורט",tour:"סיורים",other:"אחר"};
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let bank={media:[],stats:{}};
function imageUrl(item){
  const u=item.url||"";
  if(!u)return "";
  if(/^(https?:|data:)/.test(u))return u;
  const city=(item.cities||[])[0];
  return city?("../"+city+"/"+u):u;
}
function textHay(item){
  return [item.media_id,item.credit,item.rights_status,item.strategy,...(item.artists||[]),...(item.productions||[]),...(item.categories||[]),...(item.cities||[]),...(item.events||[]).map(e=>e.title)].filter(Boolean).join(" ").toLowerCase();
}
function renderStats(){
  const s=bank.stats||{};
  const stats=[
    [s.unique_images||0,"תמונות ייחודיות","ללא שכפול לפי אירוע"],
    [s.approved||0,"מאושרות","מותרות לשימוש לפי נתוני המקור"],
    [s.needs_review||0,"לבדיקה","טרם אושרו סופית"],
    [s.rejected||0,"פסולות","לא יוצגו כאפשרות"],
    [s.image_links||0,"שימושים באירועים","קישורים בין תמונות לאירועים"]
  ];
  $("mediaStats").innerHTML=stats.map(([n,t,d])=>'<article class="stat"><strong>'+n+'</strong><span>'+t+'</span><small>'+d+'</small></article>').join("");
}
function buildFilters(){
  const cities=[...new Set(bank.media.flatMap(x=>x.cities||[]))].sort();
  $("mediaCity").innerHTML='<option value="">כל הערים</option>'+cities.map(x=>'<option value="'+esc(x)+'">'+esc(x==="rishon-lezion"?"ראשון לציון":x==="ashdod"?"אשדוד":x)+'</option>').join("");
  const cats=[...new Set(bank.media.flatMap(x=>x.categories||[]))].sort();
  $("mediaCategory").innerHTML='<option value="">כל הקטגוריות</option>'+cats.map(x=>'<option value="'+esc(x)+'">'+esc(LABELS[x]||x)+'</option>').join("");
}
function filtered(){
  const q=$("mediaQ").value.trim().toLowerCase(),city=$("mediaCity").value,cat=$("mediaCategory").value,status=$("mediaStatus").value;
  return bank.media.filter(x=>{
    if(q&&!textHay(x).includes(q))return false;
    if(city&&!(x.cities||[]).includes(city))return false;
    if(cat&&!(x.categories||[]).includes(cat))return false;
    if(status&&x.status!==status)return false;
    return true;
  });
}
function render(){
  renderStats();
  const rows=filtered();
  $("mediaCount").textContent=rows.length+" תמונות מוצגות מתוך "+bank.media.length;
  $("mediaEmpty").hidden=rows.length>0;
  $("mediaGrid").innerHTML=rows.slice(0,800).map(x=>{
    const img=imageUrl(x);
    const badge=x.status==="approved"?"good":x.status==="rejected"?"bad":"warn";
    const status=x.status==="approved"?"מאושרת":x.status==="rejected"?"פסולה":"לבדיקה";
    const artists=(x.artists||[]).slice(0,3).join(" · ");
    const productions=(x.productions||[]).slice(0,2).join(" · ");
    const cats=(x.categories||[]).map(c=>LABELS[c]||c).join(" · ");
    const cities=(x.cities||[]).map(c=>c==="ashdod"?"אשדוד":c==="rishon-lezion"?"ראשון לציון":c).join(" · ");
    return '<article class="media-card">'+
      '<div class="media-img-wrap">'+(img?'<img loading="lazy" src="'+esc(img)+'" alt="">':'<div class="media-img-placeholder">אין תמונה</div>')+
      '<span class="tag '+badge+' media-badge">'+status+'</span></div>'+
      '<div class="media-card-body">'+
      '<h3>'+esc(artists||productions||"נכס מדיה")+'</h3>'+
      (productions?'<p class="media-production">'+esc(productions)+'</p>':'')+
      '<div class="media-meta">'+
      (cats?'<span>'+esc(cats)+'</span>':'')+
      (cities?'<span>'+esc(cities)+'</span>':'')+
      '<span>'+esc(String(x.usage_count||0))+' שימושים</span>'+
      (x.ai_generated?'<span>AI</span>':'')+
      '</div>'+
      '<small>'+esc(x.credit||x.rights_status||"ללא קרדיט")+'</small>'+
      '</div></article>';
  }).join("");
}
async function load(){
  const r=await fetch("../media-bank/data/media.json",{cache:"no-store"});
  if(!r.ok)throw new Error("media bank unavailable");
  bank=await r.json();
  buildFilters();render();
}
["mediaQ","mediaCity","mediaCategory","mediaStatus"].forEach(id=>$(id).addEventListener("input",render));
$("mediaClear").addEventListener("click",()=>{["mediaQ","mediaCity","mediaCategory","mediaStatus"].forEach(id=>$(id).value="");render()});
load().catch(err=>{$("mediaCount").textContent="בנק המדיה עדיין נבנה";console.error(err)});

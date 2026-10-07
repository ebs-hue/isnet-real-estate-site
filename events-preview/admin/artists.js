const LABELS={music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים",theatre:"תיאטרון",lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה",sport:"ספורט",tour:"סיורים",other:"אחר"};
const $=id=>document.getElementById(id); const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let artists=[],mediaById=new Map();
function imgFor(a){for(const id of a.media||[]){const m=mediaById.get(id);if(!m||m.status!=="approved")continue;const u=m.card_url||m.url||"";if(!u)continue;if(/^(https?:|data:)/.test(u))return u;if(u.startsWith("media-bank/"))return "../"+u;const city=(m.cities||[])[0];return city?("../"+city+"/"+u):u;}return "";}
function render(){
 const q=$("artistQ").value.trim().toLowerCase(),city=$("artistCity").value,cat=$("artistCategory").value;
 const rows=artists.filter(a=>{if(q&&!a.name.toLowerCase().includes(q))return false;if(city&&!(a.cities||[]).includes(city))return false;if(cat&&!(a.categories||[]).includes(cat))return false;return true;});
 $("artistCount").textContent=rows.length+" אמנים מוצגים מתוך "+artists.length;$("artistEmpty").hidden=rows.length>0;
 const withMedia=artists.filter(a=>a.media?.some(id=>mediaById.get(id)?.status==="approved")).length;
 $("artistStats").innerHTML=[[artists.length,"אמנים שזוהו","מתוך מידע האירועים"],[withMedia,"עם תמונה מאושרת","זמינה לשימוש חוזר"],[artists.length-withMedia,"ללא תמונה מאושרת","דורשים מחקר מקור"]].map(([n,t,d])=>'<article class="stat"><strong>'+n+'</strong><span>'+t+'</span><small>'+d+'</small></article>').join("");
 $("artistGrid").innerHTML=rows.map(a=>{const img=imgFor(a);const url="media.html?q="+encodeURIComponent(a.name);return '<article class="artist-card">'+(img?'<img loading="lazy" src="'+esc(img)+'" alt="">':'<div class="artist-placeholder">אין תמונה</div>')+'<div class="artist-body"><h3>'+esc(a.name)+'</h3><p>'+esc((a.categories||[]).map(x=>LABELS[x]||x).join(" · "))+'</p><small>'+esc((a.cities||[]).map(x=>x==="ashdod"?"אשדוד":x==="rishon-lezion"?"ראשון לציון":x).join(" · "))+' · '+esc(a.media?.length||0)+' תמונות</small><a class="edit-link" href="'+esc(url)+'">פתח בבנק המדיה</a></div></article>';}).join("");
}
async function load(){
 const [a,m]=await Promise.all([fetch("../media-bank/data/artists.json",{cache:"no-store"}).then(r=>r.json()),fetch("../media-bank/data/media.json",{cache:"no-store"}).then(r=>r.json())]);
 artists=a.artists||[];mediaById=new Map((m.media||[]).map(x=>[x.media_id,x]));
 const cities=[...new Set(artists.flatMap(x=>x.cities||[]))].sort();$("artistCity").innerHTML='<option value="">כל הערים</option>'+cities.map(x=>'<option value="'+esc(x)+'">'+esc(x==="ashdod"?"אשדוד":x==="rishon-lezion"?"ראשון לציון":x)+'</option>').join("");
 const cats=[...new Set(artists.flatMap(x=>x.categories||[]))].sort();$("artistCategory").innerHTML='<option value="">כל הקטגוריות</option>'+cats.map(x=>'<option value="'+esc(x)+'">'+esc(LABELS[x]||x)+'</option>').join("");
 render();
}
["artistQ","artistCity","artistCategory"].forEach(id=>$(id).addEventListener("input",render));load().catch(err=>{$("artistCount").textContent="מאגר האמנים עדיין נבנה";console.error(err)});

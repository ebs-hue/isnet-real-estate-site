const cityMap={"ashdod":{name:"אשדוד",base:"../ashdod/"},"rishon-lezion":{name:"ראשון לציון",base:"../rishon-lezion/"}};
const $=id=>document.getElementById(id);
const params=new URLSearchParams(location.search);
const city=params.get("city"),id=params.get("id");
const cfg=cityMap[city];
let original=null,currentImageData=null,taxonomy=null;
const OVERRIDE_KEY="isnet-event-overrides";

function draftKey(){return "isnet-event-draft:"+city+":"+id}
function readOverrides(){try{return JSON.parse(localStorage.getItem(OVERRIDE_KEY)||"{}")}catch{return{}}}
async function saveOverride(status){
  const payload={...collect(),status};
  try{
    await window.ISNET_DB.saveEventRecord(city,id,payload,"override");
    localStorage.removeItem(draftKey());
    $("status").value=status;
    $("saveNote").textContent=status==="hidden"?"האירוע הוסתר ונשמר במערכת.":status==="archived"?"האירוע הועבר לארכיון ונשמר במערכת.":"האירוע הועבר לסל ונשמר במערכת.";
  }catch(err){
    const map=readOverrides();map[city+":"+id]={status,updated_at:new Date().toISOString()};localStorage.setItem(OVERRIDE_KEY,JSON.stringify(map));
    $("saveNote").textContent="לא ניתן היה לשמור בשרת; נשמר גיבוי מקומי.";
    console.error(err);
  }
  setTimeout(()=>location.href="./",700);
}
function setOptions(selected=""){
  const items=taxonomy?.primary_categories||[];
  $("category").innerHTML=items.map(item=>'<option value="'+item.id+'" '+(item.id===selected?'selected':'')+'>'+item.label+'</option>').join("");
}
function renderSubcategories(categoryId,selected=""){
  const cat=(taxonomy?.primary_categories||[]).find(x=>x.id===categoryId);
  const items=cat?.subcategories||[];
  $("subcategory").innerHTML='<option value="">בחרו תת־קטגוריה</option>'+items.map(item=>'<option value="'+item.id+'" '+(item.id===selected?'selected':'')+'>'+item.label+'</option>').join("");
}
function renderTaxonomy(containerId,items,selected=[]){
  const selectedSet=new Set(selected||[]);
  $(containerId).innerHTML=(items||[]).map(item=>'<label class="tax-option"><input type="checkbox" value="'+item.id+'" '+(selectedSet.has(item.id)||selectedSet.has(item.label)?'checked':'')+'><span>'+item.label+'</span></label>').join("");
}
function selectedTaxonomy(containerId){return Array.from($(containerId).querySelectorAll('input[type="checkbox"]:checked')).map(x=>x.value)}
function renderAllTaxonomies(e={}){
  renderTaxonomy("secondaryCategories",taxonomy.secondary_categories,e.secondary_categories||[]);
  renderTaxonomy("audiencesText",taxonomy.audiences,e.audiences||[]);
  renderTaxonomy("topics",taxonomy.topics,e.topics||[]);
  const orgs=(taxonomy.organizations||[]).filter(x=>!x.cities||x.cities.includes(city));
  renderTaxonomy("organizations",orgs,e.organizations||[]);
  renderTaxonomy("distributionTargets",taxonomy.distribution_targets,e.distribution_targets||[]);
}
function makeSlug(value){
  return String(value||"").normalize("NFKC").trim().toLowerCase()
    .replace(/["'״׳]/g,"")
    .replace(/[^\p{L}\p{N}]+/gu,"-")
    .replace(/^-+|-+$/g,"")
    .slice(0,90);
}
function imageUrl(e){const raw=e.thumbnail_url||e.image_url||"";return raw?(/^(https?:|data:)/.test(raw)?raw:cfg.base+raw):""}
function fill(e,ed={}){
  $("title").value=e.title||"";
  $("shortPitch").value=ed.short_pitch||e.short_pitch||"";
  $("description").value=ed.long_description||e.long_description||e.series_description||e.description||"";
  $("category").value=e.category||""; renderSubcategories($("category").value,e.subcategory||""); $("status").value=e.status||"active"; $("promotion").value=e.promotion||"normal";
  renderAllTaxonomies(e);
  $("smartDistribution").checked=e.smart_distribution!==false;
  $("seoTitle").value=e.seo_title||e.title||"";
  $("seoDescription").value=e.seo_description||ed.short_pitch||e.short_pitch||"";
  $("seoSlug").value=e.seo_slug||makeSlug(e.title||"");
  $("schemaType").value=e.schema_type||"Event";
  $("seoIndex").checked=e.seo_index!==false;
  $("promoteHome").checked=e.promote_home===true;
  $("promoteCity").checked=e.promote_city!==false;
  $("promoteSection").checked=e.promote_section!==false;
  $("startDate").value=e.start_date||""; $("startTime").value=e.start_time||"";
  $("venue").value=e.venue||""; $("address").value=e.address||"";
  $("purchaseUrl").value=e.purchase_url||e.ticket_url||"";
  $("youtubeId").value=ed.youtube_id||e.youtube_id||"";
  $("imageCredit").value=e.image_credit||"";
  $("imageApproved").checked=e.image_publishable===true&&e.image_verified===true;
  const img=imageUrl(e); currentImageData=null;
  $("imagePreview").style.backgroundImage=img?'url("'+img.replace(/"/g,"%22")+'")':"none";
  $("imageState").innerHTML=img?($("imageApproved").checked?'<span class="tag good">יש תמונה · מאושרת</span>':'<span class="tag warn">יש תמונה · לבדיקה</span>'):'<span class="tag bad">אין תמונה</span>';
}
function collect(){
  return {event_id:id,city:cfg.name,title:$("title").value.trim(),short_pitch:$("shortPitch").value.trim(),long_description:$("description").value.trim(),category:$("category").value,subcategory:$("subcategory").value||null,secondary_categories:selectedTaxonomy("secondaryCategories"),audiences:selectedTaxonomy("audiencesText"),topics:selectedTaxonomy("topics"),organizations:selectedTaxonomy("organizations"),distribution_targets:selectedTaxonomy("distributionTargets"),smart_distribution:$("smartDistribution").checked,seo_title:$("seoTitle").value.trim(),seo_description:$("seoDescription").value.trim(),seo_slug:$("seoSlug").value.trim(),schema_type:$("schemaType").value,seo_index:$("seoIndex").checked,promote_home:$("promoteHome").checked,promote_city:$("promoteCity").checked,promote_section:$("promoteSection").checked,status:$("status").value,promotion:$("promotion").value,start_date:$("startDate").value,start_time:$("startTime").value,venue:$("venue").value.trim(),address:$("address").value.trim(),purchase_url:$("purchaseUrl").value.trim(),youtube_id:$("youtubeId").value.trim(),image_credit:$("imageCredit").value.trim(),image_approved:$("imageApproved").checked,image_data_url:currentImageData,updated_at:new Date().toISOString()};
}
async function load(){
  if(!cfg||!id)throw Error("missing params");
  taxonomy=await fetch("data/taxonomy.json",{cache:"no-store"}).then(r=>r.json());
  setOptions();
  const [data,editorial]=await Promise.all([
    fetch(cfg.base+"data/events.json",{cache:"no-store"}).then(r=>r.json()),
    fetch(cfg.base+"data/editorial.json",{cache:"no-store"}).then(r=>r.ok?r.json():{events:{}}).catch(()=>({events:{}}))
  ]);
  const e=(data.events||[]).find(x=>x.event_id===id); if(!e)throw Error("event not found");
  original={event:e,editorial:editorial.events?.[id]||{}};
  $("pageTitle").textContent=e.title; $("pageMeta").textContent=cfg.name+" · "+(e.start_date||"");
  const dbRecord=await window.ISNET_DB?.getEventRecord?.(city,id);
  const saved=localStorage.getItem(draftKey());
  if(dbRecord?.payload){
    const d=dbRecord.payload;fill({...e,...d},{...original.editorial,...d});$("saveNote").textContent="נטענה הגרסה השמורה במערכת המרכזית.";if(d.image_data_url){currentImageData=d.image_data_url;$("imagePreview").style.backgroundImage='url("'+d.image_data_url+'")'}
  } else if(saved){
    const d=JSON.parse(saved);fill({...e,...d},{...original.editorial,...d});$("saveNote").textContent="נטענה טיוטת גיבוי מקומית.";if(d.image_data_url){currentImageData=d.image_data_url;$("imagePreview").style.backgroundImage='url("'+d.image_data_url+'")'}
  } else fill(e,original.editorial);
}
$("category").addEventListener("change",()=>renderSubcategories($("category").value));
$("imageFile").addEventListener("change",e=>{
  const file=e.target.files?.[0];if(!file)return;
  if(file.size>5*1024*1024){alert("התמונה גדולה מ־5MB. בחר תמונה קטנה יותר.");e.target.value="";return}
  const reader=new FileReader();reader.onload=()=>{currentImageData=reader.result;$("imagePreview").style.backgroundImage='url("'+reader.result+'")';$("imageApproved").checked=false;$("imageState").innerHTML='<span class="tag warn">תמונה חדשה · דורשת אישור</span>'};reader.readAsDataURL(file);
});
let dirty=false;
function markDirty(){
  dirty=true;
  const btn=$("saveDraftBtn");
  if(!btn.disabled) btn.textContent="שמור שינויים";
  $("saveNote").textContent="יש שינויים שעדיין לא נשמרו.";
}
$("saveDraftBtn").addEventListener("click",async()=>{
  const btn=$("saveDraftBtn"),payload=collect();
  btn.disabled=true;btn.textContent="שומר...";
  $("saveNote").textContent="שומר את השינויים במערכת...";
  try{
    await window.ISNET_DB.saveEventRecord(city,id,payload,"override");
    localStorage.removeItem(draftKey());
    dirty=false;
    btn.textContent="נשמר ✓";
    $("saveNote").textContent="נשמר במערכת המרכזית ב־"+new Date().toLocaleTimeString("he-IL",{hour:"2-digit",minute:"2-digit"});
  }catch(err){
    localStorage.setItem(draftKey(),JSON.stringify(payload));
    btn.textContent="נשמר גיבוי מקומי";
    $("saveNote").textContent="לא ניתן היה לשמור בשרת. נשמר גיבוי מקומי בדפדפן.";
    console.error(err);
  }finally{
    btn.disabled=false;
  }
});
document.querySelectorAll(".editor-column input,.editor-column textarea,.editor-column select,.side-column input,.side-column textarea,.side-column select").forEach(el=>{
  el.addEventListener("input",markDirty);
  el.addEventListener("change",markDirty);
});
$("hideBtn").addEventListener("click",()=>saveOverride("hidden"));
$("archiveBtn").addEventListener("click",()=>saveOverride("archived"));
$("trashBtn").addEventListener("click",()=>{if(confirm("להעביר את האירוע לסל? אפשר יהיה לשחזר אותו בהמשך."))saveOverride("trashed")});
$("restoreBtn").addEventListener("click",async()=>{if(!original)return;
  localStorage.removeItem(draftKey());const map=readOverrides();delete map[city+":"+id];localStorage.setItem(OVERRIDE_KEY,JSON.stringify(map));
  try{await window.ISNET_DB.deleteEventRecord(city,id)}catch(err){console.error(err)}
  fill(original.event,original.editorial);$("saveNote").textContent="חזרת לנתוני המקור והגרסה השמורה הוסרה.";
});
$("previewBtn").addEventListener("click",()=>{if(!cfg||!id)return;window.open(cfg.base+"event.html?id="+encodeURIComponent(id),"_blank","noopener")});
load().catch(err=>{$("pageTitle").textContent="לא ניתן לטעון את האירוע";$("pageMeta").textContent=String(err.message||err)});

async function publishCurrentEvent(){
  const btn=$("publishBtn");
  const payload=collect();
  if(!payload.title||!payload.start_date){
    alert("אי אפשר לפרסם בלי כותרת ותאריך.");
    return;
  }
  if(!payload.seo_slug){
    payload.seo_slug=makeSlug(payload.title);
    $("seoSlug").value=payload.seo_slug;
  }
  btn.disabled=true;
  btn.textContent="מפרסם...";
  $("saveNote").textContent="מפרסם את הגרסה הנוכחית...";
  try{
    const row=await window.ISNET_DB.publishEvent(city,id,payload,"override");
    $("status").value="published";
    dirty=false;
    btn.textContent="פורסם ✓";
    const slug=row?.seo_slug||payload.seo_slug;
    const preview=cfg.base+"event.html?slug="+encodeURIComponent(slug);
    $("saveNote").innerHTML='האירוע פורסם במערכת המרכזית. <a class="link" target="_blank" rel="noopener" href="'+preview+'">פתח את העמוד הציבורי ↗</a>';
  }catch(err){
    console.error(err);
    btn.textContent="פרסום נכשל";
    $("saveNote").textContent="לא ניתן היה לפרסם. ודא שמיגרציית הפרסום הופעלה ב-Supabase ונסה שוב.";
  }finally{
    btn.disabled=false;
  }
}
$("publishBtn")?.addEventListener("click",publishCurrentEvent);

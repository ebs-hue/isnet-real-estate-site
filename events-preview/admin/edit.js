const categoryLabels={music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים",theatre:"תיאטרון",lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה",sport:"ספורט",tour:"סיורים",other:"אחר"};
const cityMap={"ashdod":{name:"אשדוד",base:"../ashdod/"},"rishon-lezion":{name:"ראשון לציון",base:"../rishon-lezion/"}};
const $=id=>document.getElementById(id);
const params=new URLSearchParams(location.search);
const city=params.get("city"),id=params.get("id");
const cfg=cityMap[city];
let original=null,currentImageData=null;
const OVERRIDE_KEY="isnet-event-overrides";

function draftKey(){return "isnet-event-draft:"+city+":"+id}
function readOverrides(){try{return JSON.parse(localStorage.getItem(OVERRIDE_KEY)||"{}")}catch{return{}}}
function saveOverride(status){
  const map=readOverrides();map[city+":"+id]={status,updated_at:new Date().toISOString()};localStorage.setItem(OVERRIDE_KEY,JSON.stringify(map));
  $("status").value=status;$("saveNote").textContent=status==="hidden"?"האירוע סומן כמוסתר.":status==="archived"?"האירוע הועבר לארכיון.":"האירוע הועבר לסל.";
  setTimeout(()=>location.href="./",500);
}
function setOptions(){ $("category").innerHTML=Object.entries(categoryLabels).map(([v,l])=>'<option value="'+v+'">'+l+'</option>').join("") }
function imageUrl(e){const raw=e.thumbnail_url||e.image_url||"";return raw?(/^(https?:|data:)/.test(raw)?raw:cfg.base+raw):""}
function fill(e,ed={}){
  $("title").value=e.title||"";
  $("shortPitch").value=ed.short_pitch||e.short_pitch||"";
  $("description").value=ed.long_description||e.long_description||e.series_description||e.description||"";
  $("category").value=e.category||"other"; $("status").value=e.status||"active"; $("promotion").value=e.promotion||"normal";
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
  return {event_id:id,city:cfg.name,title:$("title").value.trim(),short_pitch:$("shortPitch").value.trim(),long_description:$("description").value.trim(),category:$("category").value,status:$("status").value,promotion:$("promotion").value,start_date:$("startDate").value,start_time:$("startTime").value,venue:$("venue").value.trim(),address:$("address").value.trim(),purchase_url:$("purchaseUrl").value.trim(),youtube_id:$("youtubeId").value.trim(),image_credit:$("imageCredit").value.trim(),image_approved:$("imageApproved").checked,image_data_url:currentImageData,updated_at:new Date().toISOString()};
}
async function load(){
  if(!cfg||!id)throw Error("missing params");
  setOptions();
  const [data,editorial]=await Promise.all([
    fetch(cfg.base+"data/events.json",{cache:"no-store"}).then(r=>r.json()),
    fetch(cfg.base+"data/editorial.json",{cache:"no-store"}).then(r=>r.ok?r.json():{events:{}}).catch(()=>({events:{}}))
  ]);
  const e=(data.events||[]).find(x=>x.event_id===id); if(!e)throw Error("event not found");
  original={event:e,editorial:editorial.events?.[id]||{}};
  $("pageTitle").textContent=e.title; $("pageMeta").textContent=cfg.name+" · "+(e.start_date||"");
  const saved=localStorage.getItem(draftKey());
  if(saved){const d=JSON.parse(saved);fill({...e,...d},{...original.editorial,...d});$("saveNote").textContent="נטענה טיוטה שנשמרה בדפדפן.";if(d.image_data_url){currentImageData=d.image_data_url;$("imagePreview").style.backgroundImage='url("'+d.image_data_url+'")'}}
  else fill(e,original.editorial);
}
$("imageFile").addEventListener("change",e=>{
  const file=e.target.files?.[0];if(!file)return;
  if(file.size>5*1024*1024){alert("התמונה גדולה מ־5MB. בחר תמונה קטנה יותר.");e.target.value="";return}
  const reader=new FileReader();reader.onload=()=>{currentImageData=reader.result;$("imagePreview").style.backgroundImage='url("'+reader.result+'")';$("imageApproved").checked=false;$("imageState").innerHTML='<span class="tag warn">תמונה חדשה · דורשת אישור</span>'};reader.readAsDataURL(file);
});
$("saveDraftBtn").addEventListener("click",()=>{localStorage.setItem(draftKey(),JSON.stringify(collect()));$("saveNote").textContent="הטיוטה נשמרה בדפדפן ב־"+new Date().toLocaleTimeString("he-IL",{hour:"2-digit",minute:"2-digit"});});
$("hideBtn").addEventListener("click",()=>saveOverride("hidden"));
$("archiveBtn").addEventListener("click",()=>saveOverride("archived"));
$("trashBtn").addEventListener("click",()=>{if(confirm("להעביר את האירוע לסל? אפשר יהיה לשחזר אותו בהמשך."))saveOverride("trashed")});
$("restoreBtn").addEventListener("click",()=>{if(!original)return;localStorage.removeItem(draftKey());const map=readOverrides();delete map[city+":"+id];localStorage.setItem(OVERRIDE_KEY,JSON.stringify(map));fill(original.event,original.editorial);$("saveNote").textContent="חזרת לנתוני המקור.";});
$("previewBtn").addEventListener("click",()=>{if(!cfg||!id)return;window.open(cfg.base+"event.html?id="+encodeURIComponent(id),"_blank","noopener")});
load().catch(err=>{$("pageTitle").textContent="לא ניתן לטעון את האירוע";$("pageMeta").textContent=String(err.message||err)});

const categoryLabels={music:"מוזיקה",standup:"סטנדאפ",kids:"ילדים",theatre:"תיאטרון",lecture:"הרצאות",exhibition:"תערוכות",workshop:"סדנאות",cinema:"קולנוע",festival:"פסטיבלים",community:"קהילה",sport:"ספורט",tour:"סיורים",other:"אחר"};
const $=id=>document.getElementById(id);
const KEY="isnet-new-events";
let imageData=null;
function read(){try{return JSON.parse(localStorage.getItem(KEY)||"[]")}catch{return[]}}
function write(v){localStorage.setItem(KEY,JSON.stringify(v))}
function splitList(v){return String(v||"").split(/[,;\n]/).map(x=>x.trim()).filter(Boolean)}
function idFor(city){return "manual_"+city.replace(/[^a-z0-9]+/gi,"_")+"_"+Date.now()}
$("category").innerHTML=Object.entries(categoryLabels).map(([v,l])=>'<option value="'+v+'">'+l+'</option>').join("");
$("imageFile").addEventListener("change",e=>{
  const file=e.target.files?.[0];if(!file)return;
  if(file.size>5*1024*1024){alert("התמונה גדולה מ־5MB. בחר תמונה קטנה יותר.");e.target.value="";return}
  const reader=new FileReader();reader.onload=()=>{imageData=reader.result;$("imagePreview").style.backgroundImage='url("'+reader.result+'")';$("imageApproved").checked=false;$("imageState").innerHTML='<span class="tag warn">תמונה חדשה · דורשת אישור</span>'};reader.readAsDataURL(file);
});
$("saveBtn").addEventListener("click",()=>{
  const title=$("title").value.trim(),date=$("startDate").value,city=$("city").value;
  if(!title||!date){alert("יש להזין לפחות כותרת ותאריך.");return}
  const item={
    event_id:idFor(city),_citySlug:city,city:city==="ashdod"?"אשדוד":"ראשון לציון",
    title,short_pitch:$("shortPitch").value.trim(),long_description:$("description").value.trim(),
    category:$("category").value,secondary_categories:splitList($("secondaryCategories").value),audiences:splitList($("audiencesText").value),topics:splitList($("topics").value),organizations:splitList($("organizations").value),distribution_targets:splitList($("distributionTargets").value),smart_distribution:$("smartDistribution").checked,seo_title:$("seoTitle").value.trim(),seo_description:$("seoDescription").value.trim(),seo_slug:$("seoSlug").value.trim(),schema_type:$("schemaType").value,seo_index:$("seoIndex").checked,promote_home:$("promoteHome").checked,promote_city:$("promoteCity").checked,promote_section:$("promoteSection").checked,promotion:$("promotion").value,status:"draft",start_date:date,start_time:$("startTime").value,
    venue:$("venue").value.trim(),address:$("address").value.trim(),
    purchase_url:$("purchaseUrl").value.trim(),youtube_id:$("youtubeId").value.trim(),
    image_credit:$("imageCredit").value.trim(),image_publishable:$("imageApproved").checked,
    image_verified:$("imageApproved").checked,image_url:imageData||null,thumbnail_url:imageData||null,
    thumbnail_ready:Boolean(imageData),sources:[{name:"manual_entry",source_type:"editorial"}],
    observed_at:new Date().toISOString(),updated_at:new Date().toISOString()
  };
  const list=read();list.unshift(item);write(list);
  $("saveNote").textContent="האירוע נשמר כטיוטה. מחזיר לרשימה...";
  setTimeout(()=>location.href="./?status=draft",500);
});
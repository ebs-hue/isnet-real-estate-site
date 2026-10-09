const $=id=>document.getElementById(id);
const KEY="isnet-new-events";
let imageData=null,taxonomy=null;
function read(){try{return JSON.parse(localStorage.getItem(KEY)||"[]")}catch{return[]}}
function write(v){localStorage.setItem(KEY,JSON.stringify(v))}
function renderTaxonomy(containerId,items){
  $(containerId).innerHTML=(items||[]).map(item=>'<label class="tax-option"><input type="checkbox" value="'+item.id+'"><span>'+item.label+'</span></label>').join("");
}
function selectedTaxonomy(containerId){return Array.from($(containerId).querySelectorAll('input[type="checkbox"]:checked')).map(x=>x.value)}
function renderPrimaryCategories(selected=""){
  const items=taxonomy?.primary_categories||[];
  $("category").innerHTML=items.map(item=>'<option value="'+item.id+'" '+(item.id===selected?'selected':'')+'>'+item.label+'</option>').join("");
}
function renderSubcategories(categoryId,selected=""){
  const cat=(taxonomy?.primary_categories||[]).find(x=>x.id===categoryId);
  const items=cat?.subcategories||[];
  $("subcategory").innerHTML='<option value="">בחרו תת־קטגוריה</option>'+items.map(item=>'<option value="'+item.id+'" '+(item.id===selected?'selected':'')+'>'+item.label+'</option>').join("");
}
async function loadTaxonomy(){
  taxonomy=await fetch("data/taxonomy.json",{cache:"no-store"}).then(r=>r.json());
  renderPrimaryCategories();
  renderSubcategories($("category").value);
  renderTaxonomy("secondaryCategories",taxonomy.secondary_categories);
  renderTaxonomy("audiencesText",taxonomy.audiences);
  renderTaxonomy("topics",taxonomy.topics);
  renderTaxonomy("distributionTargets",taxonomy.distribution_targets);
  renderOrganizations();
}
function renderOrganizations(){
  if(!taxonomy)return;
  const city=$("city").value;
  renderTaxonomy("organizations",(taxonomy.organizations||[]).filter(x=>!x.cities||x.cities.includes(city)));
}
function makeSlug(value){
  return String(value||"").normalize("NFKC").trim().toLowerCase()
    .replace(/["'״׳]/g,"")
    .replace(/[^\p{L}\p{N}]+/gu,"-")
    .replace(/^-+|-+$/g,"")
    .slice(0,90);
}
function idFor(city){return "manual_"+city.replace(/[^a-z0-9]+/gi,"_")+"_"+Date.now()}
function normEventText(v){
  return String(v||"").normalize("NFKC").toLowerCase()
    .replace(/[\u0591-\u05c7]/g,"")
    .replace(/["'״׳]/g,"")
    .replace(/[^0-9a-zא-ת]+/g," ")
    .replace(/\s+/g," ").trim();
}
async function existingEventsForCity(city){
  const base=city==="ashdod"?"../ashdod/":"../rishon-lezion/";
  const [data,records]=await Promise.all([
    fetch(base+"data/events.json",{cache:"no-store"}).then(r=>r.json()).catch(()=>({events:[]})),
    (window.ISNET_DB?.listEventRecords?.()||Promise.resolve([])).catch(()=>[])
  ]);
  const db=(records||[])
    .filter(r=>r.city_slug===city)
    .map(r=>({...(r.payload||{}),event_id:r.event_id,_citySlug:r.city_slug}));
  return [...(data.events||[]),...db,...read().filter(e=>e._citySlug===city)];
}
async function editorialGate(candidate){
  const events=await existingEventsForCity(candidate._citySlug);
  const nt=normEventText(candidate.title), nv=normEventText(candidate.venue);
  const exact=events.find(e=>
    normEventText(e.title)===nt &&
    String(e.start_date||"")===String(candidate.start_date||"") &&
    (!nv || !e.venue || normEventText(e.venue)===nv)
  );
  if(exact)return {decision:"stop_duplicate",event:exact};

  const sameProduction=events.find(e=>
    normEventText(e.title)===nt &&
    String(e.start_date||"")!==String(candidate.start_date||"")
  );
  if(sameProduction)return {decision:"existing_production_new_occurrence",event:sameProduction};

  return {decision:"open_new_process"};
}
$("imageFile").addEventListener("change",e=>{
  const file=e.target.files?.[0];if(!file)return;
  if(file.size>5*1024*1024){alert("התמונה גדולה מ־5MB. בחר תמונה קטנה יותר.");e.target.value="";return}
  const reader=new FileReader();reader.onload=()=>{imageData=reader.result;$("imagePreview").style.backgroundImage='url("'+reader.result+'")';$("imageApproved").checked=false;$("imageState").innerHTML='<span class="tag warn">תמונה חדשה · דורשת אישור</span>'};reader.readAsDataURL(file);
});
$("saveBtn").addEventListener("click",async()=>{
  const title=$("title").value.trim(),date=$("startDate").value,city=$("city").value;
  if(!title||!date){alert("יש להזין לפחות כותרת ותאריך.");return}
  const selectedCategory=(taxonomy?.primary_categories||[]).find(x=>x.id===$("category").value);
  const selectedSubcategory=$("subcategory").value;
  if(!selectedCategory){
    alert("יש לבחור קטגוריה ראשית מתוך המילון המאושר.");return;
  }
  if(selectedSubcategory&&!selectedCategory.subcategories?.some(x=>x.id===selectedSubcategory)){
    alert("תת־הקטגוריה אינה שייכת לקטגוריה הראשית שנבחרה.");return;
  }
  const item={
    event_id:idFor(city),_citySlug:city,city:city==="ashdod"?"אשדוד":"ראשון לציון",
    title,short_pitch:$("shortPitch").value.trim(),long_description:$("description").value.trim(),
    category:$("category").value,subcategory:$("subcategory").value||null,secondary_categories:selectedTaxonomy("secondaryCategories"),audiences:selectedTaxonomy("audiencesText"),topics:selectedTaxonomy("topics"),organizations:selectedTaxonomy("organizations"),distribution_targets:selectedTaxonomy("distributionTargets"),smart_distribution:$("smartDistribution").checked,seo_title:$("seoTitle").value.trim(),seo_description:$("seoDescription").value.trim(),seo_slug:$("seoSlug").value.trim()||makeSlug(title),schema_type:$("schemaType").value,seo_index:$("seoIndex").checked,promote_home:$("promoteHome").checked,promote_city:$("promoteCity").checked,promote_section:$("promoteSection").checked,promotion:$("promotion").value,status:"draft",start_date:date,start_time:$("startTime").value,
    venue:$("venue").value.trim(),address:$("address").value.trim(),
    purchase_url:$("purchaseUrl").value.trim(),youtube_id:$("youtubeId").value.trim(),
    image_credit:$("imageCredit").value.trim(),image_publishable:$("imageApproved").checked,
    image_verified:$("imageApproved").checked,image_url:imageData||null,thumbnail_url:imageData||null,
    thumbnail_ready:Boolean(imageData),sources:[{name:"manual_entry",source_type:"editorial"}],
    observed_at:new Date().toISOString(),updated_at:new Date().toISOString()
  };

  $("saveNote").textContent="בודק אם האירוע כבר קיים במערכת...";
  try{
    const gate=await editorialGate(item);
    if(gate.decision==="stop_duplicate"){
      $("saveNote").textContent="התהליך נעצר: האירוע כבר קיים במערכת.";
      alert("האירוע הזה כבר קיים במערכת ולכן לא נפתח אירוע חדש.");
      return;
    }
    if(gate.decision==="existing_production_new_occurrence"){
      const ok=confirm("נמצאה כבר אותה הפקה במערכת במועד אחר. ייתכן שזה מועד נוסף של אותו מופע. להמשיך וליצור רשומה חדשה בכל זאת?");
      if(!ok){
        $("saveNote").textContent="התהליך נעצר כדי למנוע כפילות. יש לצרף את המועד להפקה הקיימת.";
        return;
      }
      item.editorial_gate_decision="existing_production_new_occurrence";
      item.related_event_id=gate.event?.event_id||null;
    }else{
      item.editorial_gate_decision="open_new_process";
    }
  }catch(err){
    console.warn("editorial gate unavailable",err);
  }

  try{
    await window.ISNET_DB.saveEventRecord(city,item.event_id,item,"manual");
    $("saveNote").textContent="האירוע נשמר במערכת המרכזית כטיוטה. מחזיר לרשימה...";
  }catch(err){
    const list=read();list.unshift(item);write(list);
    $("saveNote").textContent="השרת לא היה זמין; נשמר גיבוי מקומי.";
    console.error(err);
  }
  setTimeout(()=>location.href="./?status=draft",700);
});
$("city").addEventListener("change",renderOrganizations);
$("category").addEventListener("change",()=>renderSubcategories($("category").value));
loadTaxonomy().catch(console.error);

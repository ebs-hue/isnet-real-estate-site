(function(){
const CITY_CONFIG=[
  {slug:"ashdod",name:"אשדוד",base:"../ashdod/"},
  {slug:"rishon-lezion",name:"ראשון לציון",base:"../rishon-lezion/"}
];
const TODAY=new Date().toISOString().slice(0,10);
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function normalize(s){return String(s||"").normalize("NFKC").toLowerCase().replace(/[^\p{L}\p{N}]+/gu," ").trim()}
function setProgress(done,total,label){
  const wrap=$("runProgressWrap"),bar=$("runProgressBar"),txt=$("runProgressText");
  if(wrap)wrap.hidden=false;
  const pct=total?Math.round(done/total*100):0;
  if(bar)bar.style.width=pct+"%";
  if(txt)txt.textContent=(label?label+" · ":"")+done+" מתוך "+total+" ("+pct+"%)";
}
function saveRunLog(data){try{localStorage.setItem("isnet-agents-last-run",JSON.stringify(data))}catch{}}
function loadRunLog(){try{return JSON.parse(localStorage.getItem("isnet-agents-last-run")||"null")}catch{return null}}
function slugify(value){
  return String(value||"").normalize("NFKC").trim().toLowerCase()
    .replace(/["'״׳]/g,"")
    .replace(/[^\p{L}\p{N}]+/gu,"-")
    .replace(/^-+|-+$/g,"")
    .slice(0,90);
}
function stableSlug(e){
  if(e.seo_slug)return slugify(e.seo_slug);
  const base=slugify(e.title)||"event";
  const suffix=String(e.event_id||"").replace(/[^a-zA-Z0-9]+/g,"").slice(-8).toLowerCase();
  return suffix?base+"-"+suffix:base;
}
function sourceConfidence(e){
  const src=(e.sources||[])[0]?.name||e.purchase_source||"";
  if(!src)return "low";
  if(/municip|עיר|היכל|מוזיא|תרבות|official|ticket|event/i.test(src))return "high";
  return "medium";
}
function validateTaxonomy(e,taxonomy){
  const category=String(e.category||"").trim();
  if(!category)return "חסרה קטגוריה מאושרת";
  const primary=(taxonomy.primary_categories||[]).find(x=>x.id===category);
  if(!primary)return "קטגוריה אינה קיימת במילון המרכזי: "+category;
  const sub=String(e.subcategory||e.subcategory_id||"").trim();
  if(sub && !(primary.subcategories||[]).some(x=>x.id===sub))
    return "תת־קטגוריה אינה מתאימה לקטגוריה הראשית: "+sub;
  return "";
}
async function loadTaxonomy(){
  const response=await fetch("data/taxonomy.json",{cache:"no-store"});
  if(!response.ok)throw new Error("לא ניתן לטעון את מילון הקטגוריות");
  const taxonomy=await response.json();
  if(!Array.isArray(taxonomy.primary_categories)||!taxonomy.primary_categories.length)
    throw new Error("מילון הקטגוריות אינו תקין");
  return taxonomy;
}
function evaluate(e,dupes,taxonomy){
  const blockers=[],warnings=[];
  const img=e.thumbnail_url||e.image_url;
  const imageApproved=Boolean(img&&((e.image_publishable===true&&e.image_verified===true)||e.image_approved===true));
  const desc=e.long_description||e.short_pitch||e.series_description||e.description||e._description||"";
  const imageBrief=e.image_brief||"";
  const contentReady=Boolean(e.content_ready_for_media===true || String(desc).trim().length>=80 || String(imageBrief).trim().length>=40);
  if(!e.title)blockers.push("חסרה כותרת");
  if(!e.start_date)blockers.push("חסר תאריך");
  if(!e.venue)warnings.push("חסר מקום");
  const taxonomyIssue=validateTaxonomy(e,taxonomy);
  if(taxonomyIssue)blockers.push(taxonomyIssue);
  if(!contentReady)blockers.push("חסר תוכן מסביר לפני טיפול בתמונה");
  if(!img)blockers.push("אין תמונה");
  else if(!imageApproved)blockers.push("התמונה אינה מאושרת");
  if(!(e.purchase_url||e.ticket_url||e.purchase_phone))warnings.push("אין קישור פעולה");
  if(dupes.has(e._citySlug+":"+e.event_id))blockers.push("חשד לכפילות");
  const confidence=sourceConfidence(e);
  if(confidence==="low")warnings.push("מקור חלש או חסר");
  let score=100-blockers.length*22-warnings.length*8;
  score=Math.max(0,Math.min(100,score));
  const ready=blockers.length===0&&score>=72;
  const days=Math.round((new Date(e.start_date+"T12:00:00")-new Date(TODAY+"T12:00:00"))/86400000);
  let editorial="normal";
  if(ready&&days>=0&&days<=7)editorial="recommended";
  if(ready&&e.promotion==="promoted")editorial="promoted";
  return {
    score,confidence,blockers,warnings,ready,
    editorial_decision:editorial,
    publish_decision:ready?"auto_publish":"exception_queue",
    media_action:!img?(contentReady?"find_or_generate_image":"wait_for_content"):(!imageApproved?(contentReady?"review_rights":"wait_for_content"):"none")
  };
}
async function loadEvents(){
  const groups=await Promise.all(CITY_CONFIG.map(async city=>{
    const [data,editorial]=await Promise.all([
      fetch(city.base+"data/events.json",{cache:"no-store"}).then(r=>r.json()),
      fetch(city.base+"data/editorial.json",{cache:"no-store"}).then(r=>r.ok?r.json():{events:{}}).catch(()=>({events:{}}))
    ]);
    return (data.events||[]).map(e=>{
      const ed=editorial.events?.[e.event_id]||{};
      return {...e,_citySlug:city.slug,_description:ed.long_description||ed.short_pitch||e.long_description||e.short_pitch||e.description||""};
    });
  }));
  const db=await (window.ISNET_DB?.listEventRecords?.()||Promise.resolve([]));
  const map=new Map(db.map(r=>[r.city_slug+":"+r.event_id,r.payload||{}]));
  const base=groups.flat().map(e=>({...e,...(map.get(e._citySlug+":"+e.event_id)||{})}));
  const manual=db.filter(r=>r.record_type==="manual").map(r=>({...r.payload,event_id:r.event_id,_citySlug:r.city_slug}));
  const keys=new Set(base.map(e=>e._citySlug+":"+e.event_id));
  return [...base,...manual.filter(e=>!keys.has(e._citySlug+":"+e.event_id))].filter(e=>e.start_date>=TODAY&&!["archived","trashed","hidden"].includes(e.status));
}
function duplicateSet(events){
  const groups=new Map();
  for(const e of events){
    const key=[e._citySlug,e.start_date,normalize(e.title),normalize(e.venue)].join("|");
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(e);
  }
  const out=new Set();
  for(const xs of groups.values())if(xs.length>1)xs.forEach(e=>out.add(e._citySlug+":"+e.event_id));
  return out;
}
async function dbClient(){
  const cfg=window.ISNET_AUTH_CONFIG||{};
  if(!cfg.enabled||!window.supabase)return null;
  return window.supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true}});
}
async function autoPublishReady(results){
  const ready=results.filter(x=>x.result.ready);
  let published=0,alreadyPublished=0,failed=0;
  const failures=[];
  for(const {event,result} of ready){
    if(event.publication_status==="published"){
      alreadyPublished++;continue;
    }
    const payload={
      ...event,
      seo_slug:stableSlug(event),
      promotion:event.promotion||result.editorial_decision||"normal",
      agent_qa_score:result.score,
      agent_source_confidence:result.confidence,
      agent_editorial_decision:result.editorial_decision,
      agent_publish_decision:"auto_publish"
    };
    delete payload._citySlug;
    delete payload._description;
    try{
      await window.ISNET_DB.publishEvent(event._citySlug,event.event_id,payload,event._localNew?"manual":"override");
      event.publication_status="published";
      event.seo_slug=payload.seo_slug;
      published++;
    }catch(err){
      failed++;
      failures.push({event,result,error:err});
      console.error("automatic publish failed",event.event_id,err);
    }
  }
  return {published,alreadyPublished,failed,failures};
}
async function persistTasks(results){
  const db=await dbClient();if(!db)throw new Error("אין חיבור למסד הנתונים");
  const {data:{user}}=await db.auth.getUser();if(!user)throw new Error("המשתמש אינו מחובר");
  const rows=results.flatMap(({event,result})=>[
    {agent_id:"qa",entity_type:"event",entity_id:event.event_id,city_slug:event._citySlug,status:result.ready?"completed":"needs_review",input:{title:event.title,start_date:event.start_date},output:{score:result.score,confidence:result.confidence,blockers:result.blockers,warnings:result.warnings,media_action:result.media_action},confidence:result.score,created_by:user.id},
    {agent_id:"category_editor",entity_type:"event",entity_id:event.event_id,city_slug:event._citySlug,status:"completed",input:{category:event.category,start_date:event.start_date},output:{decision:result.editorial_decision},confidence:result.score,created_by:user.id},
    {agent_id:"publisher",entity_type:"event",entity_id:event.event_id,city_slug:event._citySlug,status:result.ready?"completed":"needs_review",input:{qa_score:result.score},output:{decision:result.publish_decision,reasons:result.blockers},confidence:result.score,created_by:user.id}
  ]);
  for(let i=0;i<rows.length;i+=100){
    const {error}=await db.from("agent_tasks").insert(rows.slice(i,i+100));
    if(error)throw error;
  }
}
function renderResults(results){
  const auto=results.filter(x=>x.result.ready),exceptions=results.filter(x=>!x.result.ready);
  $("runSummary").innerHTML=[
    [results.length,"אירועים שנבדקו"],
    [auto.length,"מוכנים לפרסום אוטומטי"],
    [exceptions.length,"חריגים לטיפול"],
    [results.filter(x=>x.result.media_action==="find_or_generate_image").length,"זקוקים לתמונה"],
    [results.filter(x=>x.result.media_action==="wait_for_content").length,"ממתינים לעורך תוכן"]
  ].map(([n,l])=>'<div class="run-stat"><strong>'+n+'</strong><span>'+l+'</span></div>').join("");
  $("exceptionRows").innerHTML=exceptions.slice(0,150).map(({event,result})=>'<tr>'+
    '<td><strong>'+esc(event.title)+'</strong><small>'+esc(event.event_id)+'</small></td>'+
    '<td>'+esc(event.city||event._citySlug)+'</td>'+
    '<td>'+esc(event.start_date||"—")+'</td>'+
    '<td><span class="score '+(result.score>=70?"mid":"low")+'">'+result.score+'%</span></td>'+
    '<td>'+result.blockers.map(x=>'<span class="tag bad">'+esc(x)+'</span>').join(" ")+(result.warnings.length?'<div class="warnings">'+result.warnings.map(x=>esc(x)).join(" · ")+'</div>':'')+'</td>'+
    '<td>'+ (result.media_action==="wait_for_content"?'<span class="tag bad">ממתין לעורך תוכן</span>':result.media_action==="find_or_generate_image"?'<span class="tag warn">סוכן תמונות</span>':'<span class="tag">QA</span>') +'</td>'+
    '</tr>').join("");
  $("exceptionsEmpty").hidden=exceptions.length>0;
  $("lastRun").textContent="הרצה אחרונה: "+new Date().toLocaleString("he-IL");
}
async function run(){
  const btn=$("runAgentsBtn");btn.disabled=true;btn.textContent="הסוכנים בודקים...";
  $("runStatus").textContent="טוען אירועים ומבצע בקרת איכות...";
  try{
    const taxonomy=await loadTaxonomy();
    const events=await loadEvents(),dupes=duplicateSet(events);
    const results=events.map(event=>({event,result:evaluate(event,dupes,taxonomy)}));
    renderResults(results);
    $("runStatus").textContent="הבדיקה הסתיימה. סוכן הפרסום מפרסם את האירועים התקינים...";
    const publication=await autoPublishReady(results);
    try{
      await persistTasks(results);
    }catch(err){
      console.error("agent task log unavailable",err);
    }
    const exceptionCount=results.filter(x=>!x.result.ready).length+publication.failed;
    $("runStatus").textContent=
      "ההרצה הושלמה: "+publication.published+" פורסמו אוטומטית, "+
      publication.alreadyPublished+" כבר היו מפורסמים, "+
      exceptionCount+" נשארו בתור החריגים.";
    if(publication.failed){
      $("runStatus").textContent+=" "+publication.failed+" אירועים תקינים נכשלו טכנית בפרסום ונשארו לטיפול.";
    }
  }catch(err){
    console.error(err);$("runStatus").textContent="אירעה שגיאה בהרצת הסוכנים.";
  }finally{btn.disabled=false;btn.textContent="הרץ סוכנים ופרסם תקינים"}
}
$("runStatus").textContent="המנוע מוכן להפעלה.";
$("runAgentsBtn")?.addEventListener("click",run);
})();

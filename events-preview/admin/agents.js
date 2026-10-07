const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
fetch("data/agents.json",{cache:"no-store"}).then(r=>r.json()).then(data=>{
 const byId=new Map(data.agents.map(a=>[a.id,a]));
 $("pipeline").innerHTML=data.workflow.map((id,i)=>{
   if(id==="ready_for_review")return '<div class="pipeline-step"><strong>מוכן לאישור</strong><small>עורך אנושי</small></div>';
   const a=byId.get(id);return '<div class="pipeline-step"><strong>'+esc(a?.name||id)+'</strong><small>שלב '+(i+1)+'</small></div>';
 }).join("");
 $("agentsGrid").innerHTML=data.agents.map(a=>'<article class="agent-card '+(a.status==="priority"?"priority":"")+'">'+
 '<div class="agent-head"><div><h3>'+esc(a.name)+'</h3><span class="agent-status '+(a.status==="priority"?"priority":"")+'">'+(a.status==="priority"?"בעדיפות בנייה":"מתוכנן")+'</span></div><strong>#'+a.order+'</strong></div>'+
 '<p>'+esc(a.purpose)+'</p>'+
 (a.strategy?'<div class="capabilities">'+a.strategy.map(x=>'<span class="tag">'+esc(x)+'</span>').join("")+'</div>':'')+
 '<div class="capabilities">'+a.can.slice(0,5).map(x=>'<span class="tag good">'+esc(x.replaceAll("_"," "))+'</span>').join("")+'</div>'+
 '</article>').join("");
 const steps=[
  ["1","בנק המדיה","חיפוש קודם בתמונות שכבר אושרו ברשת."],
  ["2","מקורות מורשים","חיפוש רק במקורות שאושרו לשימוש."],
  ["3","יצירת AI","אם לא נמצאה תמונה מתאימה, יצירת אילוסטרציה רלוונטית."],
  ["4","זכויות וקרדיט","שמירת מקור, קרדיט, סטטוס זכויות וסימון AI."],
  ["5","אישור מערכת","התמונה עוברת לבקרת איכות ולעורך הקטגוריה לפני פרסום."]
 ];
 $("mediaFlow").innerHTML=steps.map(([n,t,d])=>'<div class="media-step"><strong>'+n+'. '+t+'</strong><span>'+d+'</span></div>').join("");
}).catch(console.error);
const KEY="isnet-cms-users";
const $=id=>document.getElementById(id);
let config=null;
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function loadUsers(){try{const x=JSON.parse(localStorage.getItem(KEY)||"[]");if(x.length)return x}catch{}return[{id:"owner-1",display_name:"מנהל־על ראשי",email:"",role:"super_admin",sites:["all"],modules:["events","articles","sports","classes","real-estate","media","taxonomy","homepage","users","settings"],active:true,created_at:new Date().toISOString()}]}
function saveUsers(v){localStorage.setItem(KEY,JSON.stringify(v))}
function roleBy(id){return config.roles.find(x=>x.id===id)}
function labelBy(list,id){return list.find(x=>x.id===id)?.label||id}
function render(){
 const users=loadUsers(),active=users.filter(x=>x.active).length,admins=users.filter(x=>["super_admin","admin","site_admin"].includes(x.role)&&x.active).length;
 $("summary").innerHTML=[
  [users.length,"משתמשים"],[active,"פעילים"],[admins,"מנהלים"],[config.roles.length,"תפקידים"]
 ].map(([n,l])=>'<div class="summary-item"><strong>'+n+'</strong><span>'+l+'</span></div>').join("");
 $("userRows").innerHTML=users.map(u=>'<tr>'+
  '<td><div class="user-name">'+esc(u.display_name)+'</div><div class="user-email">'+esc(u.email||"ללא אימייל בפיילוט")+'</div></td>'+
  '<td><span class="role-badge">'+esc(roleBy(u.role)?.label||u.role)+'</span></td>'+
  '<td><div class="scope-tags">'+(u.sites||[]).map(x=>'<span class="tag">'+esc(labelBy(config.sites,x))+'</span>').join("")+'</div></td>'+
  '<td><div class="scope-tags">'+(u.modules||[]).slice(0,5).map(x=>'<span class="tag">'+esc(labelBy(config.modules,x))+'</span>').join("")+((u.modules||[]).length>5?'<span class="tag">+'+((u.modules||[]).length-5)+'</span>':'')+'</div></td>'+
  '<td><span class="role-badge '+(u.active?"state-active":"state-disabled")+'">'+(u.active?"פעיל":"מושבת")+'</span></td>'+
  '<td><button class="edit-link edit-user" data-id="'+esc(u.id)+'">עריכה ✎</button></td></tr>').join("");
 $("rolesGrid").innerHTML=config.roles.map(r=>'<article class="role-card"><h3>'+esc(r.label)+'</h3><p>'+esc(r.description)+'</p><div class="permission-list">'+(r.permissions.includes("*")?'<span class="tag good">כל ההרשאות</span>':r.permissions.map(p=>'<span class="tag">'+esc(labelBy(config.actions,p))+'</span>').join(""))+'</div></article>').join("");
 document.querySelectorAll(".edit-user").forEach(b=>b.onclick=()=>openDrawer(b.dataset.id));
}
function renderOptions(container,items,selected=[]){
 const set=new Set(selected||[]);
 $(container).innerHTML=items.map(x=>'<label class="permission-option"><input type="checkbox" value="'+x.id+'" '+(set.has(x.id)?'checked':'')+'><span>'+x.label+'</span></label>').join("");
}
function selected(container){return Array.from($(container).querySelectorAll('input:checked')).map(x=>x.value)}
function renderEffective(){
 const r=roleBy($("role").value);$("effectivePermissions").innerHTML=(r?.permissions||[]).includes("*")?'<span class="tag good">כל ההרשאות</span>':(r?.permissions||[]).map(x=>'<span class="tag">'+esc(labelBy(config.actions,x))+'</span>').join("");
}
function openDrawer(id=null){
 const users=loadUsers(),u=id?users.find(x=>x.id===id):null;
 $("editingId").value=u?.id||"";$("displayName").value=u?.display_name||"";$("email").value=u?.email||"";
 $("role").innerHTML=config.roles.map(x=>'<option value="'+x.id+'">'+x.label+'</option>').join("");$("role").value=u?.role||"editor";
 renderOptions("siteOptions",config.sites,u?.sites||["ashdod"]);renderOptions("moduleOptions",config.modules,u?.modules||["events"]);
 $("active").checked=u?.active!==false;$("disableUserBtn").hidden=!u;$("drawerTitle").textContent=u?"עריכת משתמש":"הוספת משתמש";
 renderEffective();$("drawerBackdrop").hidden=false;$("userDrawer").classList.add("open");$("userDrawer").setAttribute("aria-hidden","false");
}
function closeDrawer(){$("drawerBackdrop").hidden=true;$("userDrawer").classList.remove("open");$("userDrawer").setAttribute("aria-hidden","true")}
$("addUserBtn").onclick=()=>openDrawer();
$("closeDrawer").onclick=closeDrawer;$("drawerBackdrop").onclick=closeDrawer;$("role").addEventListener("change",renderEffective);
$("saveUserBtn").onclick=()=>{
 const name=$("displayName").value.trim(),email=$("email").value.trim();if(!name){alert("יש להזין שם משתמש.");return}
 const users=loadUsers(),id=$("editingId").value||("user-"+Date.now());
 const value={id,display_name:name,email,role:$("role").value,sites:selected("siteOptions"),modules:selected("moduleOptions"),active:$("active").checked,updated_at:new Date().toISOString()};
 const i=users.findIndex(x=>x.id===id);if(i>=0)users[i]={...users[i],...value};else users.push({...value,created_at:new Date().toISOString()});
 saveUsers(users);closeDrawer();render();
};
$("disableUserBtn").onclick=()=>{const id=$("editingId").value,users=loadUsers(),i=users.findIndex(x=>x.id===id);if(i<0)return;users[i].active=false;saveUsers(users);closeDrawer();render()};
fetch("data/permissions.json",{cache:"no-store"}).then(r=>r.json()).then(x=>{config=x;render()}).catch(err=>{document.body.innerHTML="<p>שגיאה בטעינת מודל ההרשאות</p>";console.error(err)});
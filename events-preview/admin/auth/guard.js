import {authConfigured,getClient} from "./supabase.js";
export async function requireAuth({superAdminOnly=false}={}){
  if(!authConfigured()) return {pilot:true,user:null,profile:null};
  const client=getClient();
  const {data:{session}}=await client.auth.getSession();
  if(!session){location.replace("./login.html?next="+encodeURIComponent(location.pathname+location.search));return null}
  const {data:profile,error}=await client.from("profiles").select("id,email,display_name,role,is_active").eq("id",session.user.id).single();
  if(error||!profile||profile.is_active===false){await client.auth.signOut();location.replace("./login.html?blocked=1");return null}
  if(superAdminOnly&&profile.role!=="super_admin"){location.replace("./?forbidden=users");return null}
  return {pilot:false,user:session.user,profile,client};
}
export async function signOut(){
  if(!authConfigured()){location.href="./";return}
  const client=getClient();await client.auth.signOut();location.replace("./login.html");
}

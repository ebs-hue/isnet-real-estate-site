const cfg=window.ISNET_AUTH_CONFIG||{};
export function authConfigured(){
  return Boolean(cfg.enabled&&cfg.supabaseUrl&&cfg.supabaseAnonKey&&!cfg.supabaseUrl.includes("YOUR_PROJECT"));
}
export function getClient(){
  if(!authConfigured()) return null;
  if(!window.supabase) throw new Error("Supabase SDK not loaded");
  return window.supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{
    auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}
  });
}

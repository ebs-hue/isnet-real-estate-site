(function(){
  function client(){
    const cfg=window.ISNET_AUTH_CONFIG||{};
    if(!cfg.enabled||!window.supabase)return null;
    return window.supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true}});
  }
  async function userId(db){
    const {data:{user}}=await db.auth.getUser();
    return user?.id||null;
  }
  window.ISNET_DB={
    async listEventRecords(){
      const db=client();if(!db)return [];
      const {data,error}=await db.from("cms_event_records").select("*");
      if(error){console.warn("cms_event_records unavailable",error);return []}
      return data||[];
    },
    async getEventRecord(city,eventId){
      const db=client();if(!db)return null;
      const {data,error}=await db.from("cms_event_records").select("*").eq("city_slug",city).eq("event_id",eventId).maybeSingle();
      if(error){console.warn("get event record failed",error);return null}
      return data||null;
    },
    async saveEventRecord(city,eventId,payload,recordType="override"){
      const db=client();if(!db)throw new Error("database unavailable");
      const uid=await userId(db);if(!uid)throw new Error("not authenticated");
      const row={city_slug:city,event_id:eventId,record_type:recordType,payload,status:payload.status||null,updated_by:uid,updated_at:new Date().toISOString()};
      const {data,error}=await db.from("cms_event_records").upsert(row,{onConflict:"city_slug,event_id"}).select().single();
      if(error)throw error;return data;
    },
    async publishEvent(city,eventId,payload,recordType="override"){
      const db=client();if(!db)throw new Error("database unavailable");
      const uid=await userId(db);if(!uid)throw new Error("not authenticated");
      const slug=String(payload.seo_slug||"").trim();
      if(!slug)throw new Error("missing slug");
      const publishedAt=new Date().toISOString();
      const publicPath="/events/"+slug;
      const publicPayload={...payload,status:"active",publication_status:"published",published_at:publishedAt,public_path:publicPath};
      const row={
        city_slug:city,event_id:eventId,record_type:recordType,payload:publicPayload,
        status:"active",seo_slug:slug,publication_status:"published",
        published_at:publishedAt,public_path:publicPath,updated_by:uid,updated_at:publishedAt
      };
      const {data,error}=await db.from("cms_event_records").upsert(row,{onConflict:"city_slug,event_id"}).select().single();
      if(error)throw error;return data;
    },
    async unpublishEvent(city,eventId,payload,recordType="override"){
      const db=client();if(!db)throw new Error("database unavailable");
      const uid=await userId(db);if(!uid)throw new Error("not authenticated");
      const row={
        city_slug:city,event_id:eventId,record_type:recordType,payload:{...payload,publication_status:"unpublished"},
        status:payload.status||"active",seo_slug:payload.seo_slug||null,publication_status:"unpublished",
        updated_by:uid,updated_at:new Date().toISOString()
      };
      const {data,error}=await db.from("cms_event_records").upsert(row,{onConflict:"city_slug,event_id"}).select().single();
      if(error)throw error;return data;
    },
    async deleteEventRecord(city,eventId){
      const db=client();if(!db)throw new Error("database unavailable");
      const {error}=await db.from("cms_event_records").delete().eq("city_slug",city).eq("event_id",eventId);
      if(error)throw error;return true;
    }
  };
})();
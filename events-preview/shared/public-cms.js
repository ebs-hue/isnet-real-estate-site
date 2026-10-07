(function(){
  const url="https://qomkxhafrprooekwgsxf.supabase.co";
  const key="sb_publishable_njxvSKmgkOQqkGL3JbWiIA_od-9l3wb";
  window.ISNET_PUBLIC_CMS={
    async publishedEvents(citySlug){
      const endpoint=url+"/rest/v1/cms_event_records?city_slug=eq."+encodeURIComponent(citySlug)+"&publication_status=eq.published&select=event_id,record_type,payload,seo_slug,publication_status,published_at,public_path";
      const r=await fetch(endpoint,{headers:{apikey:key,Authorization:"Bearer "+key},cache:"no-store"});
      if(!r.ok){console.warn("Published CMS events unavailable",r.status);return []}
      return r.json();
    }
  };
})();
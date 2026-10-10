/* ISNET editorial safety, 2026-10-10.
 * Defense in depth only. Database policies and server-side publishing validation
 * are still required before automated publication can resume.
 */
(function(){
  "use strict";
  const publicTextFields=[
    "long_description","short_pitch","description","series_description",
    "event_summary","seo_description","seo_title","suitability","youtube_note"
  ];
  const privateKey=/^(?:editorial_|internal_|audit_|review_|qa_|missing_information$|source_detail_text$|content_enrichment_source$|source_urls$)/i;
  const blocked=[
    /https?:\/\//i,
    /(?:העמוד|המקור|עמוד האירוע) (?:אינו מפרט|לא מפרט|לא מציין)/,
    /(?:יש|נדרש) (?:לבדוק|לאמת|לברר|לעיין|בירור)/,
    /(?:לא ניתן לאמת|לא נמצאו פרטים|לפני פרסום|שים לב:)/,
    /(?:לפי|על פי) (?:עמוד|אתר|האתר|מקור|המקור|הפרסום|המידע|FRIENDS|סמארטיקט|טיקצ.אק)/,
    /(?:באתר|בעמוד) (?:האירוע|הכרטיסים|ההרשמה|המקור) (?:נכתב|מפורט|מצוין|מופיעים)/,
    /(?:הסבירות גבוהה|לא צוין במקור|לא ברור מן המקור)/,
    /(?:editorial_questions|internal_review_notes|source_urls|content_ready_for_media)/i
  ];
  function problems(value){
    if(typeof value!=="string")return ["not_text"];
    const text=value.trim();
    if(!text)return ["empty"];
    return blocked.filter(pattern=>pattern.test(text)).map(pattern=>String(pattern));
  }
  function publicText(value){
    return typeof value==="string" && !problems(value).length ? value.trim() : "";
  }
  function validateForPublish(payload){
    const errors=[];
    if(!payload || typeof payload!=="object")return ["missing_payload"];
    for(const [field,min,max] of [["long_description",110,10000],["short_pitch",35,350]]){
      const v=payload[field];
      if(typeof v!=="string" || v.trim().length<min || v.length>max)errors.push(field+":length");
      else if(problems(v).length)errors.push(field+":internal_note_or_source");
    }
    for(const field of publicTextFields){
      if(field==="long_description"||field==="short_pitch")continue;
      const value=payload[field];
      if(value && problems(String(value)).length)errors.push(field+":internal_note_or_source");
    }
    for(const field of ["highlights","performers","creators"]){
      if(Array.isArray(payload[field]) && payload[field].some(x=>typeof x==="string"&&problems(x).length)){
        errors.push(field+":internal_note_or_source");
      }
    }
    return errors;
  }
  function sanitizePublicEvent(payload){
    if(!payload || typeof payload!=="object" || Array.isArray(payload))return {};
    const out={};
    for(const [key,value] of Object.entries(payload)){
      if(privateKey.test(key))continue;
      if(publicTextFields.includes(key))out[key]=publicText(value);
      else if(["highlights","performers","creators"].includes(key) && Array.isArray(value)){
        out[key]=value.map(publicText).filter(Boolean);
      }else out[key]=value;
    }
    return out;
  }
  window.ISNET_EDITORIAL_SAFETY={problems,publicText,validateForPublish,sanitizePublicEvent};
})();

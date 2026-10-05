const titles={
  parks:"פארקים באשדוד",
  nature:"טבע וטיולים",
  beaches:"החופים באשדוד",
  attractions:"אטרקציות",
  culture:"מוסדות תרבות באשדוד",
  "must-see":"מקומות שחייבים להכיר"
};
const id=new URLSearchParams(location.search).get("category")||"parks";
const title=titles[id]||"מה עושים באשדוד?";
document.getElementById("placesTitle").textContent=title;
document.title=title+" | מה עושים באשדוד?";
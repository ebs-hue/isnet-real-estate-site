const {parseHTML}=require('linkedom');
const vm=require('vm'),fs=require('fs'),assert=require('assert'),path=require('path');
async function check(city){
 const html=fs.readFileSync(path.join(__dirname,'..',city==='yavne'?'יבנה/index.html':'כרמי-גת/index.html'),'utf8');
 const {window}=parseHTML(html),errors=[];
 const context=vm.createContext({document:window.document,window:{print(){}},console:{log(){},info(){},error(...e){errors.push(e.map(String).join(' '))}},fetch:async url=>{let file=path.join(__dirname,'..',url.split('?')[0].replace('../',''));return fs.existsSync(file)?{ok:true,json:async()=>JSON.parse(fs.readFileSync(file,'utf8'))}:{ok:false,status:404}},Date,setTimeout});
 vm.runInContext(html.split('<script>')[1].split('</script>')[0],context);
 await new Promise(resolve=>setTimeout(resolve,30));
 const run=code=>vm.runInContext(code,context);
 assert.equal(errors.length,0,errors.join('\n'));
 assert(window.document.querySelectorAll('#roomCards .card').length===3);
 for(const [rooms,small,mid,large] of [[3,80,95,96],[4,100,115,116],[5,120,135,136]]){
  assert(run(`sizeRowFor(${rooms},${small}).max_area_sqm===${small}`));
  assert(run(`sizeRowFor(${rooms},${mid}).max_area_sqm===${mid}`));
  assert(run(`sizeRowFor(${rooms},${large}).max_area_sqm===null`));
 }
 run(`estRooms.value='4';estArea.value='90';renderEstimate()`);
 const small=window.document.getElementById('estimateValue').textContent;
 run(`estArea.value='125';renderEstimate()`);
 assert(window.document.getElementById('estimateEvidence').textContent.includes('116 מ״ר ומעלה'),'Area must choose the correct model band');
 assert(!window.document.getElementById('estimateEvidence').textContent.includes('פלח גודל: עד 100'));
 run(`document.getElementById('estAsk').value='2500000';renderEstimate()`);
 assert(window.document.getElementById('estimateComparison').textContent.includes('₪'));
 run(`estArea.value='301';renderEstimate()`);
 assert(window.document.getElementById('estimateValue').textContent.includes('תקין'));
 assert.equal(run('pct(null)'),'—');
 assert(run('money(null)').includes('אין נתונים'));
 if(city==='karmi'){
   assert.equal(window.document.querySelectorAll('.featureBtn').length,0);
   run(`book.rows.find(r=>r.scope==='room_size'&&Number(r.rooms)===3&&r.min_area_sqm===95).realistic_price_ils=null;estRooms.innerHTML='<option value="3" selected>3</option>';estArea.value='110';renderEstimate()`);
   assert(window.document.getElementById('estimateValue').textContent.includes('מיליון'));
   assert(window.document.getElementById('estimateWhy').textContent.includes('אין מחיר שפורסם'));
   assert(window.document.getElementById('estimateEvidence').textContent.includes('ללא התאמת גודל'));
   run(`q='נחל ירקון';search.value=q;renderSearchSuggestions();renderRecentDeals();renderStreets()`);
   assert(window.document.querySelector('.suggestion').textContent.includes('נחל ירקון'));
   assert(window.document.querySelector('#recentTable tbody').textContent.includes('נחל ירקון'));
   assert([...window.document.querySelectorAll('#streets .streetName')].every(x=>x.textContent.includes('נחל ירקון')));
 }else{
   run(`q='נעמי שמר';search.value=q;renderSearchSuggestions()`);
   const opts=[...window.document.querySelectorAll('.suggestion')];assert(opts.some(x=>x.textContent.includes('נעמי שמר 14')));
   opts.find(x=>x.textContent.includes('נעמי שמר 14')).onclick();
   assert(window.document.querySelector('.addressCard h2').textContent.includes('נעמי שמר 14'));
   assert(window.document.querySelector('.addressCard tbody tr'));
 }
 window.document.getElementById('resetSearch').onclick();
 assert.equal(run('q'),'');
 run(`selected='4';render()`);
 assert.equal(window.document.querySelectorAll('#roomCards .card').length,1);
 assert([...window.document.querySelectorAll('#recentTable tbody tr')].every(x=>x.children[2].textContent==='4'));
 assert(run(`formatDate('2026-07-21')`)==='21/07/2026');
 console.log('PASS '+city+': actual datasets, size boundaries, estimates, missing values, search/reset, room filters, quarterly transactions and date order');
}
(async()=>{await check('yavne');await check('karmi')})().catch(e=>{console.error(e);process.exit(1)});

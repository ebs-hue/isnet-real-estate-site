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
 assert(window.document.querySelector('#estimateComparables h3'));
 const comparable=run(`comparableDeals(4,125,'')`);
 assert(comparable.length<=5);
 assert(comparable.every(r=>Number(r.room_num)===4&&Math.abs(Number(r.asset_area)-125)/125<=.2));
 const original=run('quarterData');
 context.mockQuarter={period_from:'2026-07-01',period_to:'2026-09-30',rows:[
 {_usable_standard_full_apartment:true,_event_date_iso:'2026-08-01',room_num:'4',asset_area:'120',deal_amount:'2000000',gush:'1',chelka:'2',sub_chelka:'1',_neighborhood:'א'},
 {_usable_standard_full_apartment:true,_event_date_iso:'2026-08-01',room_num:'4',asset_area:'120',deal_amount:'2000000',gush:'1',chelka:'2',sub_chelka:'1',_neighborhood:'א'},
 {_usable_standard_full_apartment:true,_event_date_iso:'2026-10-01',room_num:'4',asset_area:'120',deal_amount:'2000000'},
 {_usable_standard_full_apartment:true,_event_date_iso:'2026-08-01',room_num:'5',asset_area:'120',deal_amount:'2000000'},
 {_usable_standard_full_apartment:true,_event_date_iso:'2026-08-01',room_num:'4',asset_area:'160',deal_amount:'2000000'},
 {_usable_standard_full_apartment:false,_event_date_iso:'2026-08-01',room_num:'4',asset_area:'120',deal_amount:'2000000'}]};
 context.mockQuarter.city=run('book.city');context.mockQuarter.rows.forEach(r=>r.settlement=context.mockQuarter.city);context.mockQuarter.rows.push({...context.mockQuarter.rows[0],settlement:'גן יבנה',sub_chelka:'99'});run('quarterData=mockQuarter');assert.equal(run(`comparableDeals(4,100,'א').length`),1);
 assert.equal(run(`comparableDeals(4,100,'ב').length`),0);
 run(`renderEstimateComparables(3,100,'')`);assert(window.document.getElementById('estimateComparables').textContent.includes('לא נמצאו'));
 context.originalQuarter=original;run('quarterData=originalQuarter');assert(run('quarterRows().length')>0);if(city==='yavne'){assert.equal(run('quarterRows().length'),25);assert(run('quarterRows().every(r=>r.settlement==="יבנה")'));assert(run("comparableDeals(4,110,'').length")>0)}

 run(`document.getElementById('estAsk').value='2500000';renderEstimate()`);
 assert(window.document.getElementById('estimateComparison').textContent.includes('₪'));
 run(`estArea.value='301';renderEstimate()`);
 assert(window.document.getElementById('estimateValue').textContent.includes('תקין'));
 assert.equal(run('pct(null)'),'—');assert.equal(run("listingFallback({realistic_price_ils:null,median_asking_price_ils:2000000,active_listing_count:3,publication_status:'learning'}).estimate_ils"),1850000);assert.equal(run("listingFallback({realistic_price_ils:1900000,median_asking_price_ils:2000000,active_listing_count:3})"),null);assert.equal(run("listingFallback({realistic_price_ils:null,median_asking_price_ils:2000000,active_listing_count:2})"),null);
 assert(run('money(null)').includes('אין נתונים'));
 if(city==='karmi'){
   assert.equal(window.document.querySelectorAll('.featureBtn').length,0);
   run(`Object.assign(book.rows.find(r=>r.scope==='room_size'&&Number(r.rooms)===3&&r.min_area_sqm===95),{realistic_price_ils:null,listing_fallback:null,median_asking_price_ils:2000000,active_listing_count:4});estRooms.innerHTML='<option value="3" selected>3</option>';estArea.value='110';renderEstimate()`);
   assert(window.document.getElementById('estimateValue').textContent.includes('מיליון'));
   assert(window.document.getElementById('estimateWhy').textContent.includes('אומדן מהלוחות בלבד'));assert(window.document.getElementById('estimateWhy').textContent.includes('7.5%'));assert.equal(run("listingFallback(sizeRowFor(3,110)).estimate_ils"),1850000);
   assert(window.document.getElementById('estimateEvidence').textContent.includes('מבוסס מודעות'));
   run(`q='נחל ירקון';search.value=q;renderSearchSuggestions();renderRecentDeals();renderStreets()`);
   assert(window.document.querySelector('.suggestion').textContent.includes('נחל ירקון'));
   assert(window.document.querySelector('#recentTable tbody').textContent.includes('נחל ירקון'));
   assert([...window.document.querySelectorAll('#streets .streetName')].every(x=>x.textContent.includes('נחל ירקון')));
 }else{
   const oldInventory=run('inventoryData'),oldNeighborhoods=run('neighborhoodPricebooks');
   context.syntheticInventory={rows:[1,2,3].map(i=>({neighborhood:'בדיקה',rooms:4,area_sqm:110,asking_price_ils:2000000}))};
   run('inventoryData=syntheticInventory;neighborhoodPricebooks={neighborhoods:{}}');
   assert.equal(run("neighborhoodFallback('בדיקה',4,110).estimate_ils"),1850000);
   run('inventoryData.rows.pop()');assert.equal(run("neighborhoodFallback('בדיקה',4,110)"),null);
   run("inventoryData=syntheticInventory;neighborhoodPricebooks={neighborhoods:{'בדיקה':{review_rows:[{rooms:4}]}}}");assert.equal(run("neighborhoodFallback('בדיקה',4,110)"),null);
   context.oldInventory=oldInventory;context.oldNeighborhoods=oldNeighborhoods;run('inventoryData=oldInventory;neighborhoodPricebooks=oldNeighborhoods');
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
(async()=>{await check('yavne');await check('karmi');const report=await require('./qa-estimate-scenarios.cjs').scenarios();console.log('PASS '+report.cases.length+' observed estimator scenarios')})().catch(e=>{console.error(e);process.exit(1)});

const {parseHTML}=require('linkedom');
const vm=require('vm'),fs=require('fs'),path=require('path'),assert=require('assert');
async function scenarios(root=path.join(__dirname,'..')){
 const report={kind:'functional_observed_listing_scenarios',note:'Checks estimator behavior on saved listing facts; asking prices are not closed-sale ground truth.',cases:[]};
 for(const city of ['yavne','karmi']){
  const html=fs.readFileSync(path.join(root,city==='yavne'?'יבנה/index.html':'כרמי-גת/index.html'),'utf8');
  const inventory=JSON.parse(fs.readFileSync(path.join(root,city==='yavne'?'data/yavne/inventory.json':'data/karmi-gat-inventory.json'),'utf8'));
  const {window}=parseHTML(html),errors=[];
  const context=vm.createContext({document:window.document,window:{print(){}},console:{log(){},info(){},error(...args){errors.push(args.join(' '))}},fetch:async url=>{const p=path.join(root,url.split('?')[0].replace('../',''));return fs.existsSync(p)?{ok:true,json:async()=>JSON.parse(fs.readFileSync(p,'utf8'))}:{ok:false,status:404}},Date,setTimeout});
  vm.runInContext(html.split('<script>')[1].split('</script>')[0],context);
  await new Promise(resolve=>setTimeout(resolve,30));
  const run=s=>vm.runInContext(s,context),chosen=[];
  for(const rooms of [3,4,5]){
   const rows=inventory.rows.filter(r=>Number(r.rooms)===rooms&&r.area_sqm>=35&&r.area_sqm<=300&&r.asking_price_ils>0).sort((a,b)=>a.area_sqm-b.area_sqm);
   assert(rows.length>=4);
   for(const i of [0,Math.floor(rows.length/2),rows.length-1]) chosen.push(rows[i]);
   if(rooms===4)chosen.push(rows[Math.floor(rows.length/4)]);
  }
  for(const row of chosen){
   // Select actual option rather than assigning a mock-only value.
   run(`estRooms.innerHTML='<option value="${row.rooms}" selected>${row.rooms}</option>';estArea.value='${row.area_sqm}';document.getElementById('estAsk').value='${row.asking_price_ils}';renderEstimate()`);
   const result=window.document.getElementById('estimateResult'),basis=window.document.getElementById('estimateBasis').textContent;
   const estimate=Number(result.dataset.estimateIls),low=Number(result.dataset.lowIls),high=Number(result.dataset.highIls);
   assert(Number.isFinite(estimate)&&estimate>0,'No estimate for observed supported listing');
   assert(low>0&&low<=estimate&&estimate<=high,'Invalid price range');
   assert(basis.includes('מועד המודל')&&basis.includes('רמת ביטחון'),'Missing evidence');
   assert(basis.includes('אינו מספר העסקאות ברבעון'),'Model and quarter periods mixed');
   assert(window.document.getElementById('estimateComparison').textContent.includes('₪'));
   const comparable=run(`comparableDeals(${row.rooms},${row.area_sqm},'')`);
   assert(comparable.every(r=>r._usable_standard_full_apartment&&Number(r.room_num)===Number(row.rooms)));
   report.cases.push({city:city==='yavne'?'יבנה':'כרמי גת',street:row.street||null,rooms:row.rooms,area_sqm:row.area_sqm,asking_price_ils:row.asking_price_ils,estimate_ils:estimate,low_ils:low,high_ils:high,asking_difference_pct:Math.round((row.asking_price_ils-estimate)/estimate*1000)/10,quarter_comparables:comparable.length});
  }
  run("estArea.value='301';renderEstimate()");
  assert.equal(window.document.getElementById('estimateBasis').textContent,'');
  assert.equal(window.document.getElementById('estimateResult').dataset.estimateIls,undefined);
  // Check that a listing-only result exposes its basis, and clearing the model leaves no stale price.
  run("renderEstimateBasis([], {listing_count:4}, 'נמוכה')");
  assert(window.document.getElementById('estimateBasis').textContent.includes('מודעות בלבד'));
  assert(!window.document.getElementById('estimateBasis').textContent.includes('פלח הגודל שנבחר'));
  assert.equal(errors.length,0,errors.join('\n'));
 }
 assert.equal(report.cases.length,20);
 return report;
}
module.exports={scenarios};
if(require.main===module)scenarios().then(r=>{if(process.env.PRICEBOOK_QA_REPORT)fs.writeFileSync(process.env.PRICEBOOK_QA_REPORT,JSON.stringify(r,null,2)+'\n');console.log('PASS 20 observed listing scenarios: positive bounded estimates, evidence, asking comparisons, supported comparable deals and stale-result clearing')}).catch(e=>{console.error(e);process.exit(1)});

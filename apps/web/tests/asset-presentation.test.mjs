import test from 'node:test';
import assert from 'node:assert/strict';
import {assetDisplayName} from '../src/lib/asset-display.ts';
import {coverageRows,technicalSources} from '../src/lib/asset-coverage.ts';
import {matchesSearch} from '../src/lib/asset-location.ts';
const a={asset_code:'RS-DT-DAM',name:'Canonical original',data_status:'REGISTERED'};
const empty={technical:[],events:[],condition:null,conditionError:false,documents:[],links:[]};
const rows=(data=empty,status='NO_LOCATION')=>Object.fromEntries(coverageRows(a,{location_status:status},data));
test('controlled aliases are presentation-only and unknown components keep real names',()=>{
 for(const code of ['DAM','SPILLWAY','INTAKE','MGMT']) assert.match(assetDisplayName({...a,asset_code:`RS-DT-${code}`}),/ — /);
 assert.equal(a.name,'Canonical original');assert.equal(assetDisplayName({...a,asset_code:'RS-CHILD'}),a.name);
 assert.equal(rows().Identity,'Available');
});
test('reference is separate from verified, no fake completeness score',()=>{
 assert.equal(rows(empty,'REFERENCE_LOCATION').Location,'Reference');assert.equal(rows().Location,'Missing');
 assert.equal(Object.keys(rows()).length,9);assert.equal(rows().Maintenance,'Absent — no verified events');
});
test('failed responses stay unavailable instead of zero',()=>{
 const r=rows({technical:null,events:null,condition:null,conditionError:true,documents:null,links:null});
 for(const key of ['Technical','Condition','Inspection','Repair','Maintenance','Documents','3D'])assert.equal(r[key],'Unavailable');
});
test('levels need bound reviewed provenance and sources deduplicate by source identity',()=>{
 const technical=[{source_id:'s',verification_status:'VERIFIED',reviewed_provenance:{verification_level:'L2'}},{source_id:'s',verification_status:'VERIFIED',reviewed_provenance:null}];
 const d={...empty,technical};assert.equal(technicalSources(d),'1 identified source');assert.match(rows(d).Technical,/level unavailable/);
});
test('candidates are excluded from category counts and model links never imply full semantics',()=>{
 const d={...empty,events:[{event_type:'MAINTENANCE',verification_status:'UNVERIFIED'}],links:[{verification_status:'VERIFIED'}]};
 assert.equal(rows(d).Maintenance,'Absent — no verified events');assert.equal(rows(d)['3D'],'Representative mapping');
});
test('search matches bilingual alias while preserving canonical search',()=>{
 const asset={...a,id:'x',category:{code:'DAM',name:'Dam'}};
 assert.equal(matchesSearch(asset,'dap chinh',''),true);assert.equal(matchesSearch(asset,'Canonical original',''),true);
});

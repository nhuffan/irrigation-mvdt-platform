import test from 'node:test';
import assert from 'node:assert/strict';
import { descendantIds, hierarchyCoverage, l2Count } from '../src/lib/asset-hierarchy.ts';
import { modelSelectionUrl, uniqueObjectLink } from '../src/lib/model-deep-link.ts';
const assets=[{id:'p',parent_asset_id:null},{id:'c',parent_asset_id:'p'},{id:'g',parent_asset_id:'c'},{id:'q',parent_asset_id:null}];
const l2={reviewed_provenance:{verification_level:'L2'}};
const records={p:[],c:[l2,l2],g:[l2,{verification_status:'VERIFIED'}],q:[l2]};
test('direct and descendant totals remain separate, nested children counted once',()=>{
 assert.deepEqual(descendantIds(assets,'p'),['c','g']);
 assert.equal(l2Count(['p'],records),0);
 assert.equal(l2Count(descendantIds(assets,'p'),records),3);
 assert.deepEqual(hierarchyCoverage(assets,records),{primary:1,components:3,all:4});
});
test('missing endpoint is unknown, not zero; VERIFIED alone is not L2',()=>{
 assert.equal(l2Count(['c'],{c:null}),null);
 assert.equal(l2Count(['missing'],records),null);
 assert.equal(l2Count(['g'],records),1);
 assert.equal(l2Count([],records),0);
});
test('cyclic input terminates without counting the selected parent',()=>{
 assert.deepEqual(descendantIds([{id:'a',parent_asset_id:'b'},{id:'b',parent_asset_id:'a'}],'a'),['b']);
});
test('selection URLs encode object keys; clearing removes stale object and preserves unrelated query',()=>{
 const href=modelSelectionUrl('http://localhost/reservoirs/r/3d?paper=1#viewer','m','node / 1');
 const u=new URL(href,'http://localhost');assert.equal(u.searchParams.get('object'),'node / 1');
 assert.equal(u.searchParams.get('paper'),'1');
 const cleared=new URL(modelSelectionUrl(u.href,'m',null),'http://localhost');
 assert.equal(cleared.searchParams.has('object'),false);assert.equal(cleared.hash,'#viewer');
});
test('ambiguous object links cannot select a child by array order',()=>{
 const links=[{object_key:'x',asset_id:'parent'},{object_key:'x',asset_id:'child'}];
 assert.equal(uniqueObjectLink(links,'x'),undefined);
 assert.equal(uniqueObjectLink(links,null),undefined);
 assert.equal(uniqueObjectLink([links[0]],'x'),links[0]);
 assert.equal(uniqueObjectLink(links,'missing'),undefined);
});
import { coverageRows } from '../src/lib/asset-coverage.ts';
test('reference location and absent O&M/files/model remain distinct from unavailability',()=>{
 const data={technical:[],events:[],condition:null,conditionError:false,documents:[],links:[]};
 const rows=Object.fromEntries(coverageRows({data_status:'REGISTERED'},{location_status:'REFERENCE_LOCATION'},data));
 assert.equal(rows.Location,'Reference');assert.equal(rows.Inspection,'Absent — no verified events');
 assert.equal(rows.Documents,'Absent — no linked files');assert.equal(rows['3D'],'Missing');
 const unavailable=Object.fromEntries(coverageRows({data_status:'REGISTERED'},{location_status:'NO_LOCATION'},{...data,events:null,links:null,documents:null}));
 assert.equal(unavailable.Inspection,'Unavailable');assert.equal(unavailable.Documents,'Unavailable');assert.equal(unavailable['3D'],'Unavailable');
});

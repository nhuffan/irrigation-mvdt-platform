import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { coverageRows, coverageTotals, knownSum } from '../src/lib/methodology-coverage.ts';
import { technicalReadback, sameReadback } from '../src/lib/methodology-readback.ts';
import { observationReferences, OBSERVATION_LAYERS } from '../src/lib/observation-map.ts';
const parent = {id:'p',asset_code:'RS-P',name:'Parent',parent_asset_id:null,geometry:null};
const child = {id:'c',asset_code:'RS-C',name:'Child',parent_asset_id:'p',geometry:null};
const tech = {id:'t',attribute_key:'height',value_number:3,value_text:null,unit:'m',source_id:'s',verification_status:'VERIFIED',reviewed_provenance:{verification_level:'L2',source_code:'RS-S',source_locator:'p1',authority:'SUPPORTING'}};
const info = {technical:[],documents:[{id:'d',checksum_sha256:'hash'}],events:[],links:[],condition:null,conditionError:false};
test('parent/child L2 is reported direct and descendant without double counting shared PDFs',()=>{
 const rows=coverageRows([parent,child],{p:info,c:{...info,technical:[tech]}});
 assert.equal(rows[0].direct_l2,0);assert.equal(rows[0].descendant_l2,1);
 assert.equal(rows[1].direct_l2,1);assert.equal(coverageTotals(rows).all_l2,1);
 assert.equal(rows[0].unique_files,1);assert.equal(rows[1].unique_files,1);
});
test('failed APIs retain unknowns while successful empty results remain zero',()=>{
 const rows=coverageRows([parent,child],{p:info,c:{...info,technical:null,events:null,documents:null,links:null,conditionError:true}});
 const totals=coverageTotals(rows);
 assert.equal(rows[0].direct_l2,0);assert.equal(rows[0].descendant_l2,null);
 assert.equal(totals.all_l2,null);assert.equal(totals.verified_om,null);
 assert.equal(rows[1].documents,null);assert.equal(rows[1].condition,null);
 assert.equal(knownSum([0,null]),null);assert.equal(knownSum([]),0);
});
test('missing geometry field is unknown rather than asserted absent',()=>{
 assert.equal(coverageRows([{...parent,geometry:undefined}],{p:info})[0].canonical_geometry,null);
});
test('same-count changes to technical values or source locators invalidate the readback',()=>{
 const baseline=technicalReadback([tech]);
 assert.ok(sameReadback(technicalReadback([tech]),baseline));
 assert.ok(!sameReadback(technicalReadback([{...tech,value_number:4}]),baseline));
 assert.ok(!sameReadback(technicalReadback([{...tech,reviewed_provenance:{...tech.reviewed_provenance,source_locator:'p2'}}]),baseline));
 assert.ok(!sameReadback(null,baseline));
});
test('observation map accepts only reviewed geographic references and never inferred or LOCAL coordinates',()=>{
 const location={location_status:'REFERENCE_LOCATION',review_state:'AVAILABLE',reviewed_at:'2026-10-15T00:00:00Z',evidence_id:'e',crs:'EPSG:4326',geometry:{type:'Point',coordinates:[106.3,11.3]}};
 const approved={...parent,location};
 const assets=[approved,{...child,geometry:{type:'Point',coordinates:[1,2]}},{...child,location:{...location,review_state:'PENDING'}},{...child,location:{...location,crs:'LOCAL'}},{...child,location:{...location,geometry:{type:'Point',coordinates:[999,999]}}}];
 assert.deepEqual(observationReferences(assets),[approved]);
 assert.ok(OBSERVATION_LAYERS.every(l=>l.tiles.startsWith('https://gibs.earthdata.nasa.gov/')&& !l.tiles.includes('token')));
});
test('controlled public summary accounts for all assets/L2 and retains original evaluation states',()=>{
 const c=JSON.parse(readFileSync(new URL('../src/data/methodology.json',import.meta.url)));
 assert.equal(c.assets.length,10);assert.equal(c.assets.filter(a=>a.scope==='primary').length,4);
 assert.equal(c.assets.reduce((n,a)=>n+a.technical_l2,0),44);
 assert.equal(c.assets.filter(a=>a.scope==='primary').reduce((n,a)=>n+a.technical_l2,0),17);
 assert.equal(c.assets.filter(a=>a.scope==='component').reduce((n,a)=>n+a.technical_l2,0),27);
 assert.equal(c.sources.length,22);assert.equal(c.sources.filter(s=>s.expected_file).length,17);
 assert.equal(c.evaluation.length,21);
 assert.equal(c.evaluation.find(f=>f.check_id==='F02').status,'FAIL');
 assert.equal(c.evaluation.find(f=>f.check_id==='F05').status,'FAIL');
 assert.equal(c.evaluation.find(f=>f.check_id==='F15').checked_at,'2026-10-14T18:13:24.540905+00:00');
 assert.equal(c.methodology.status,'NOT_READY');assert.equal(c.methodology.dataset_status,'NOT_FROZEN');
 assert.equal(c.protocol.collection_status,'NOT_COLLECTED');assert.equal(c.protocol.results,null);
 assert.ok(!/\/Users\/|storage_key|reviewer_name|reviewer_receipt/.test(JSON.stringify(c)));
});

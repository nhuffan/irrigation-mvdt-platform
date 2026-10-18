import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { coverageRows, coverageTotals, knownSum } from '../src/lib/methodology-coverage.ts';
import { technicalReadback, sameReadback } from '../src/lib/methodology-readback.ts';
import { completionFromSnapshot, snapshotVersionSupported, publicResearchValue, publicMethodologyLink, stableReadback } from "../src/lib/methodology-completion.ts";
import { completionReadback, completionAlignment } from "../src/lib/methodology-observations.ts";
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
 const textual={...tech,value_number:null,value_text:'Bê tông cốt thép (BTCT)',unit:'text'};
 assert.ok(!sameReadback(technicalReadback([{...textual,value_text:'Gạch xây'}]),technicalReadback([textual])));
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


function completionFixture() {
 const count={applicable:null,available:null,missing:null,not_applicable:null,unknown:null};
 return {schema_version:'METHODOLOGY-DASHBOARD-v2',completion:{
  schema_version:'METHODOLOGY-COMPLETION-v1',captured_at:'2026-10-18T00:00:00Z',status_definitions:[{status:'PENDING_REVIEW',definition:'Not approved'}],
  study_design:{title:'Case study',design:'Bounded',status:'PROTOCOL_ONLY',primary_denominator:4,component_count:6,scope_rationale:'Keep four primary',units:[],collection_method:[],admission_method:[]},
  maim:{status:'PENDING_REVIEW',basis:'Draft',approval_status:'PENDING_REVIEW',rows:[{asset_id:'p',asset_code:'RS-P',scope:'primary',parent_asset_code:'',category:'DAM',status:'PENDING_REVIEW',...count,proposed:{applicable:2,available:0,missing:1,not_applicable:1,unknown:1,optional:0},fields:[]},{asset_id:'c',asset_code:'RS-C',scope:'component',parent_asset_code:'RS-P',category:'DAM',status:'PENDING_REVIEW',...count,proposed:null,fields:[]}]},
  metrics:[],source_quality:{authority:[{classification:'UNKNOWN',count:1}],verification:[],review:[],dates:[],conflicts:[]},workflow:[],retrieval_tasks:[],
  baseline_protocol:{design:'Paired',status:'NOT_COLLECTED',pairing_keys:[],timing:'Timed',timeout:'Predeclare',order_and_training:'Counterbalance',analysis:'Paired',bias:'Convenience',participant_count:null,observations:null,time_results:null},
  questionnaire:{instrument:'CUSTOM_8_ITEM_NOT_SUS',status:'NOT_COLLECTED',item_count:8,scale:'1-5',analysis:'Per item',results:null},
  readiness:{status:'NOT_READY',dataset_status:'NOT_FROZEN',compiler_blocker_count:1,declared_gates:[],groups:[],accepted_gate_ids:[],unresolved_gate_ids:[],approval_summary:[],limitation:'No fresh approval'},
  provenance:{methodology_package_fingerprint:'a',previous_package_fingerprint:'a',package_status:'UNCHANGED',completion_artifact_sha256:'b',documents:[{id:'protocol',label:'Protocol',href:'https://github.com/nhuffan/irrigation-mvdt-platform/blob/main/research/evaluation/protocol.md',sha256:'c',status:'PROTOCOL_ONLY'}]}
 }};
}
test('v1 compatibility never invents v2 formal denominator or zeros',()=>{
 assert.ok(snapshotVersionSupported({schema_version:'METHODOLOGY-DASHBOARD-v1'}));
 assert.ok(snapshotVersionSupported({schema_version:'METHODOLOGY-DASHBOARD-v2'}));
 assert.equal(snapshotVersionSupported({schema_version:'METHODOLOGY-DASHBOARD-v3'}),false);
 assert.equal(completionFromSnapshot({schema_version:'METHODOLOGY-DASHBOARD-v1'}),null);
 const c=completionFromSnapshot(completionFixture());
 assert.equal(c.maim.rows[0].available,null);assert.equal(c.maim.rows[0].applicable,null);
 assert.equal(c.maim.rows[0].proposed.available,0);assert.equal(c.maim.rows[0].proposed.unknown,1);
 assert.equal(c.maim.rows[1].proposed,null);assert.equal(c.maim.rows[1].not_applicable,null);
 assert.equal(c.source_quality.authority[0].classification,'UNKNOWN');
 assert.equal(c.provenance.documents[0].href,'https://github.com/nhuffan/irrigation-mvdt-platform/blob/main/research/evaluation/protocol.md');
 assert.equal(c.baseline_protocol.participant_count,null);assert.equal(c.questionnaire.results,null);
});
test('missing or malformed completion sections fail closed to unavailable',()=>{
 for(const mutate of [c=>delete c.maim.rows[0].available,c=>c.maim.rows[0].missing=-1,c=>c.provenance.documents=null,c=>c.readiness.groups=null,c=>c.readiness.groups=[{}],c=>c.workflow=[{}],c=>c.source_quality.conflicts=[{}],c=>c.readiness.declared_gates=[null],c=>c.provenance.documents=[null]]){
  const input=completionFixture();mutate(input.completion);assert.equal(completionFromSnapshot(input),null);
 }
});
test('public summary adapter removes local paths, contacts and reviewer receipts without losing field units',()=>{
 const safe=publicResearchValue({'reviewer_independence_review.csv':'safe-hash',unit:'text',number:0,text:'Roof',reviewer_name:'Private Name',reviewer_receipt:'private.json',storage_key:'/Users/name/private.pdf',email:'private@example.com',locator:'PDF:p3',notes:'See /Users/name/data.pdf or file:///private/tmp/source.pdf contact person@example.com'});
 assert.equal(safe['reviewer_independence_review.csv'],'safe-hash');assert.equal(safe.unit,'text');assert.equal(safe.number,0);assert.equal(safe.locator,'PDF:p3');
 assert.ok(!/Private Name|private@example|\/Users\/|file:\/\/|storage_key|receipt|reviewer_name/.test(JSON.stringify(safe)));
 const input=completionFixture();input.completion.provenance.documents[0].href='file:///Users/name/private.pdf';
 input.completion.readiness.declared_gates=[{id:'G1',label:'Gate',category:'APPROVAL',required:true,status:'PENDING',decision_owner:'Private Person',blocker_group:'DOMAIN'}];
 const c=completionFromSnapshot(input);assert.equal(c.provenance.documents[0].href,null);assert.equal(c.readiness.declared_gates[0].decision_owner,'ROLE_UNAVAILABLE');
});
test('published methodology links are exact tracked public docs, never reviewed evidence or traversal',()=>{
 const base='https://github.com/nhuffan/irrigation-mvdt-platform/blob/main/';
 assert.equal(publicMethodologyLink(base+'research/evaluation/protocol.md'),base+'research/evaluation/protocol.md');
 assert.equal(publicMethodologyLink(base+'scripts/methodology_completion.py'),base+'scripts/methodology_completion.py');
 for(const p of ['research/dataset/reviewed/private.csv','research/evaluation/evidence/private.md','research/evaluation/%2e%2e/dataset/private.csv','research/evaluation/../evaluation/protocol.md','research/evaluation/protocol.md?token=abc','research/evaluation/protocol.md#private']){
  assert.equal(publicMethodologyLink(base+p),null,p);
 }
 assert.equal(publicMethodologyLink('file:///Users/private.pdf'),null);
 assert.equal(publicMethodologyLink('javascript:alert(1)'),null);
});
test('same-count drift checks source metadata, file hashes, reference coordinates and 3D identities',()=>{
 const a={...parent,category:{code:'DAM'},location:{location_status:'REFERENCE_LOCATION',review_state:'AVAILABLE',evidence_id:'e',crs:'EPSG:4326',geometry:{type:'Point',coordinates:[106,11]},reviewed_at:'2026-10-18T00:00:00Z'}};
 const rec={...info,links:[{id:'link',model_id:'m',asset_id:'p',object_key:'object',verification_status:'VERIFIED'}]};
 const source={id:'s',source_code:'RS-S',title:'Technical source',source_type:'DOCUMENT',source_date:null,authority_level:null,verification_status:'UNVERIFIED'};
 const model={id:'m',source_id:'s',model_code:'RS-M',coordinate_mode:'LOCAL',longitude:null,latitude:null,height:null,heading:0,pitch:0,roll:0,scale:1,verification_status:'UNVERIFIED'};
 const observed=completionReadback([a],{p:rec},[model],[source]);
 const c={completion:{live_readback:observed}};
 assert.equal(completionAlignment(c,observed),'RECORD_READBACK_MATCH');
 for(const mutate of [v=>v.assets['RS-P'].documents[0].checksum_sha256='different',v=>v.assets['RS-P'].location.geometry.coordinates[0]=107,v=>v.assets['RS-P'].links[0].object_key='other',v=>v.sources[0].source_date='2024-01-01',v=>v.sources[0].title='Different source',v=>v.sources[0].source_type='MODEL',v=>v.sources[0].authority_level='AUTHORITATIVE',v=>v.sources[0].verification_status='VERIFIED',v=>v.models[0].scale=2]){
  const other=structuredClone(observed);mutate(other);assert.equal(completionAlignment(c,other),'DIFFERENT_OR_UNAVAILABLE');
 }
 assert.equal(completionAlignment({},observed),'UNAVAILABLE');
 assert.notEqual(stableReadback({value:null}),stableReadback({value:0}));
 assert.equal(stableReadback({a:1,b:2}),stableReadback({b:2,a:1}));
 assert.ok(!sameReadback(technicalReadback([{...tech,unit:'cm'}]),technicalReadback([tech])));
});

test('unknown location and absent document checksum do not become zero reference coverage or a unique file',()=>{
 const unknown=coverageRows([parent],{p:{...info,documents:[{id:'d',checksum_sha256:null}]}});
 assert.equal(coverageTotals(unknown).reference_points,null);assert.equal(unknown[0].unique_files,null);
 const absent=coverageRows([{...parent,location:{location_status:'NO_LOCATION'}}],{p:{...info,documents:[]}});
 assert.equal(coverageTotals(absent).reference_points,0);assert.equal(absent[0].unique_files,0);
});

test('presentation metadata and all visible research models participate in same-count drift detection',()=>{
 const a={...parent,category:{code:'DAM',name:'Dam'}};
 const rec={...info,technical:[{...tech,attribute_label:'Height',source:{id:'s'}}],documents:[{id:'d',source_id:'s',original_file_name:'Reviewed document.pdf',checksum_sha256:'hash'}]};
 const model={id:'m',source_id:'s',model_code:'RS-M',name:'Representative model',format:'GLB',coordinate_mode:'LOCAL',longitude:null,latitude:null,height:null,heading:0,pitch:0,roll:0,scale:1,verification_status:'UNVERIFIED'};
 const baseline=completionReadback([a],{p:rec},[model],[]),c={completion:{live_readback:baseline}};
 const compare=(asset=a,record=rec,models=[model])=>completionAlignment(c,completionReadback([asset],{p:record},models,[]));
 assert.equal(compare(),'RECORD_READBACK_MATCH');
 assert.equal(compare({...a,name:'Another asset'}),'DIFFERENT_OR_UNAVAILABLE');
 assert.equal(compare({...a,category:{...a.category,name:'Another category'}}),'DIFFERENT_OR_UNAVAILABLE');
 assert.equal(compare(a,{...rec,technical:[{...rec.technical[0],attribute_label:'Wrong label'}]}),'DIFFERENT_OR_UNAVAILABLE');
 assert.equal(compare(a,{...rec,technical:[{...rec.technical[0],source:{id:'wrong-source'}}]}),'DIFFERENT_OR_UNAVAILABLE');
 assert.equal(compare(a,{...rec,documents:[{...rec.documents[0],original_file_name:'Another document.pdf'}]}),'DIFFERENT_OR_UNAVAILABLE');
 assert.equal(compare(a,rec,[{...model,name:'Another model'}]),'DIFFERENT_OR_UNAVAILABLE');
 assert.equal(compare(a,rec,[{...model,format:'glTF'}]),'DIFFERENT_OR_UNAVAILABLE');
 assert.equal(compare(a,rec,[model,{...model,id:'new',model_code:'RS-NEW'}]),'DIFFERENT_OR_UNAVAILABLE');
 // The legacy readback stays byte-compatible; v2 owns new presentation observations.
 assert.deepEqual(Object.keys(technicalReadback([tech])[0]),['id','key','number','text','unit','verification_status','source_id','level','locator','source_code','authority']);
});
test('optional render-used completion properties fail closed instead of crashing or displaying objects',()=>{
 for(const mutate of [c=>c.readiness.not_applicable_gate_ids='N/A',c=>c.readiness.not_applicable_gate_ids=[{}],c=>c.maim.dictionary={defined_entries:31,required_entries:0,status:'PENDING_REVIEW',limitation:{}},c=>c.maim.dictionary={defined_entries:{},required_entries:0,status:'PENDING_REVIEW',limitation:'Draft'},c=>c.maim.rows[0].proposed.optional={},c=>c.questionnaire.item_count={},c=>c.readiness.compiler_blocker_count={},c=>c.provenance.previous_package_fingerprint={}]){
  const input=completionFixture();mutate(input.completion);assert.equal(completionFromSnapshot(input),null);
 }
 const good=completionFixture();good.completion.readiness.not_applicable_gate_ids=['F08','F10','F11'];
 good.completion.maim.dictionary={defined_entries:31,required_entries:0,status:'PENDING_REVIEW',limitation:'Optional dictionary is not an approved denominator'};
 const c=completionFromSnapshot(good);assert.equal(c.readiness.not_applicable_gate_ids.join(' · '),'F08 · F10 · F11');assert.equal(c.maim.dictionary.required_entries,0);
});

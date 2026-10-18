import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { quantitativeFromSnapshot, quantitativeLink } from '../src/lib/methodology-quantitative.ts';
import { completionFromSnapshot } from '../src/lib/methodology-completion.ts';
const ASSET='00000000-0000-4000-8000-000000000001';
const SOURCE='00000000-0000-4000-8000-000000000002';
const DOC='00000000-0000-4000-8000-000000000003';
const counts={total_fields:2,numeric_fields:1,text_fields:1,both_value_fields:0,missing_value_fields:0,unit_present:2,unit_missing:0,unit_text:1,locator_present:2,locator_missing:0,source_linked:2,source_missing:0};
function fixture(){return {schema_version:'METHODOLOGY-DASHBOARD-v2',completion:{quantitative:{
 schema_version:'METHODOLOGY-QUANTITATIVE-v1',temporal_basis:{snapshot_captured_at:'2026-10-18T00:00:00Z',api_read_at:null,dataset_as_of:null,dataset_status:'NOT_FROZEN',rule:'Snapshot, API read and source event dates are distinct'},
 metric_dictionary:[{id:'formal',name:'Technical completeness',definition:'Requires reviewed applicability',numerator_rule:'Applicable direct fields present',denominator_rule:'Approved applicable fields',missing_rule:'Unknown stays null',na_rule:'Reviewed N/A only',temporal_basis:'Historical document',scope_policy:'Parent and component separate',basis_docs:['protocol.md']}],
 coverage:{groups:[{scope:'primary',asset_count:4,direct_l2:17,descendant_l2:27,metrics:[{metric_id:'formal',numerator:null,denominator:null,value:null,status:'PENDING_REVIEW'}]},{scope:'component',asset_count:6,direct_l2:27,descendant_l2:0,metrics:[]},{scope:'all',asset_count:10,direct_l2:44,descendant_l2:27,metrics:[]}],assets:[{asset_id:ASSET,asset_code:'RS-P',scope:'primary',parent_asset_code:'',direct_l2:0,descendant_l2:18,maim:{status:'PENDING_REVIEW',applicable:null,present:null,verified_record:null,missing:null,not_applicable:null,proposed:null},metrics:[{metric_id:'direct_presence',numerator:0,denominator:null,value:null,status:'DESCENDANTS_REPORTED_SEPARATELY'}]}]},
 field_quality:{...counts,units:[{value:'m',count:1},{value:'text',count:1}],source_status:[{value:'UNVERIFIED',count:2}],source_review_status:[{value:'REVIEWED_WITH_LIMITATIONS',count:2}],semantics:[{value:'SOURCE_REPORTED / HISTORICAL_DOCUMENTED',count:2}],by_asset:[{asset_id:ASSET,asset_code:'RS-P',category_code:'DAM',scope:'primary',...counts}],by_category:[{category_code:'DAM',total_fields:2,numeric_fields:1,text_fields:1,missing_value_fields:0}]},
 lineage:[{asset_id:ASSET,asset_code:'RS-P',source_id:SOURCE,source_code:'RS-S',field_count:2,attribute_keys:['height','material'],locators:['PDF:p3','Drawing:03A:p5'],retained_document_records:1,linked_document_records:1,availability:'RETAINED',asset_href:'/assets/'+ASSET,source_href:'/data-sources/'+SOURCE+'/documents',documents:[{id:DOC,href:'/documents/'+DOC,checksum_sha256:'a'.repeat(64)}]}],
 retained_review_blockers:[{id:'conflict',label:'Conflict register',basis_file:'conflicts.csv',entry_count:0,status_counts:[],limitation:'No evidence promotion'}],
 retrieval_feasibility:[{asset_id:ASSET,asset_code:'RS-P',scope:'primary',task_id:'T1',evidence_status:'ABSENCE_ONLY',available_records:0,answer_key_status:'PENDING_REVIEW',reason:'No reviewed answer key',asset_href:'/assets/'+ASSET}],
 empirical_metrics:[{id:'success',name:'All-attempt success',formula:'successful applicable attempts / all applicable attempts',numerator_rule:'Correct scored attempts',denominator_rule:'All applicable attempts including failures/timeouts',missing_rule:'Unobserved stays null',selection_bias:'Successful-only time is selected',status:'NOT_COLLECTED',results:null}],
 readiness_groups:[{id:'EVIDENCE',finding_count:2,status:'PENDING_EVIDENCE'}],input_hashes:{'protocol.md':'b'.repeat(64)}
}}};}
test('legacy completion is readable when quantitative extension is absent or malformed',()=>{
 const legacy=JSON.parse(readFileSync(new URL('../src/data/methodology.json',import.meta.url)));
 delete legacy.completion.quantitative;
 assert.equal(quantitativeFromSnapshot(legacy).status,'UNAVAILABLE');assert.ok(completionFromSnapshot(legacy));
 legacy.completion.quantitative={schema_version:'UNKNOWN'};
 assert.equal(quantitativeFromSnapshot(legacy).status,'INVALID_EXTENSION');assert.ok(completionFromSnapshot(legacy));
});
test('formal applicability remains unknown while real zero, text units and parent/component counts are preserved',()=>{
 const result=quantitativeFromSnapshot(fixture());assert.equal(result.status,'AVAILABLE');const q=result.data;
 assert.equal(q.coverage.groups[0].direct_l2,17);assert.equal(q.coverage.groups[1].direct_l2,27);assert.equal(q.coverage.groups[2].direct_l2,44);
 const a=q.coverage.assets[0];assert.equal(a.direct_l2,0);assert.equal(a.descendant_l2,18);assert.equal(a.maim.applicable,null);assert.equal(a.maim.not_applicable,null);assert.equal(a.metrics[0].denominator,null);assert.equal(a.metrics[0].status,'DESCENDANTS_REPORTED_SEPARATELY');
 assert.equal(q.field_quality.text_fields,1);assert.equal(q.field_quality.unit_missing,0);assert.equal(q.field_quality.units[1].value,'text');assert.equal(q.field_quality.source_status[0].value,'UNVERIFIED');
});
test('unavailable field or retrieval readback stays null and is never imputed zero or a completed task',()=>{
 const f=fixture();f.completion.quantitative.retrieval_feasibility[0].available_records=null;f.completion.quantitative.field_quality.by_asset[0].locator_present=null;
 const q=quantitativeFromSnapshot(f).data;assert.equal(q.retrieval_feasibility[0].available_records,null);assert.equal(q.field_quality.by_asset[0].locator_present,null);assert.equal(q.retrieval_feasibility[0].answer_key_status,'PENDING_REVIEW');assert.equal(q.empirical_metrics[0].results,null);
});
test('quantitative extension fails closed for malformed nested structures or invented empirical results',()=>{
 for(const mutate of [q=>q.coverage.assets[0].maim.proposed={},q=>q.coverage.groups[0].metrics='broken',q=>q.field_quality.units=[{}],q=>q.field_quality.by_asset=null,q=>q.lineage[0].locators=[{}],q=>q.lineage[0].documents=[{}],q=>q.retained_review_blockers[0].status_counts='pending',q=>q.retrieval_feasibility[0].available_records=-1,q=>q.empirical_metrics[0].results={success:1},q=>q.temporal_basis.api_read_at={},q=>q.readiness_groups[0].finding_count='71']){
  const f=fixture();mutate(f.completion.quantitative);assert.equal(quantitativeFromSnapshot(f).status,'INVALID_EXTENSION');
 }
});
test('lineage routes are derived from validated IDs and public projection discards private extras',()=>{
 const f=fixture(),q=f.completion.quantitative;q.lineage[0].asset_href='javascript:alert(1)';q.lineage[0].source_href='file:///Users/name/receipt.pdf';q.lineage[0].documents[0].href='https://private.example/source.pdf';q.lineage[0].reviewer_name='Private Person';q.metric_dictionary[0].definition='See /Users/name/original.pdf';q.input_hashes['/Users/name/private.json']='f'.repeat(64);q.review_receipt='/private/tmp/receipt.json';
 const out=quantitativeFromSnapshot(f).data;
 assert.equal(out.lineage[0].asset_href,'/assets/'+ASSET);assert.equal(out.lineage[0].source_href,'/data-sources/'+SOURCE+'/documents');assert.equal(out.lineage[0].documents[0].href,'/documents/'+DOC);assert.equal(out.lineage[0].locators[0],'PDF:p3');
 assert.ok(!/Private Person|reviewer_name|review_receipt|\/Users\/|\/private\/|private\.example/.test(JSON.stringify(out)));assert.deepEqual(Object.keys(out.input_hashes),['protocol.md']);
 assert.equal(quantitativeLink('asset','../private'),null);assert.equal(quantitativeLink('source','file:///private'),null);
});
test('controlled snapshot and source-reporting time remain distinct from current API read and dataset freeze',()=>{
 const q=quantitativeFromSnapshot(fixture()).data;
 assert.equal(q.temporal_basis.snapshot_captured_at,'2026-10-18T00:00:00Z');assert.equal(q.temporal_basis.api_read_at,null);assert.equal(q.temporal_basis.dataset_as_of,null);assert.equal(q.temporal_basis.dataset_status,'NOT_FROZEN');assert.equal(q.metric_dictionary[0].temporal_basis,'Historical document');
});

test('review date kinds are retained without substituting partial dates into canonical source age',()=>{
 const f=fixture();f.completion.quantitative.source_dates=[{source_code:'RS-S',date_kind:'event_date',date_value:'2026-03-31',status:'SOURCE_REPORTED',basis:'Existing review'},{source_code:'RS-S',date_kind:'canonical_source_date',date_value:null,status:'UNKNOWN',basis:'DB source metadata'}];
 f.completion.quantitative.source_ages=[{source_id:SOURCE,source_code:'RS-S',source_date:null,age_days:null,status:'PENDING_REVIEW'}];
 const q=quantitativeFromSnapshot(f).data;assert.equal(q.source_dates[0].date_value,'2026-03-31');assert.equal(q.source_ages[0].source_date,null);assert.equal(q.source_ages[0].age_days,null);
 f.completion.quantitative.source_dates[0].date_value={};assert.equal(quantitativeFromSnapshot(f).status,'INVALID_EXTENSION');
});

test('paired field locators and proposed N/A reasons retain scope without admitting formal exclusions',()=>{
 const f=fixture();f.completion.quantitative.lineage[0].field_locators=[{attribute_key:'height',locators:['PDF:p3']},{attribute_key:'material',locators:['Drawing:03A:p5']}];
 f.completion.quantitative.coverage.assets[0].maim.proposed_semantics='Raw presence is not verified-backed rule satisfaction';
 f.completion.quantitative.coverage.assets[0].maim.proposed_not_applicable=[{field:'three_d',reason:'Nonrequired per retained proposal',basis:'Existing 3D eligibility review'}];
 const q=quantitativeFromSnapshot(f).data;assert.equal(q.lineage[0].field_locators[1].locators[0],'Drawing:03A:p5');assert.equal(q.coverage.assets[0].maim.not_applicable,null);assert.equal(q.coverage.assets[0].maim.proposed_semantics,'Raw presence is not verified-backed rule satisfaction');assert.equal(q.coverage.assets[0].maim.proposed_not_applicable[0].field,'three_d');
 f.completion.quantitative.lineage[0].field_locators[0].locators='p3';assert.equal(quantitativeFromSnapshot(f).status,'INVALID_EXTENSION');
});

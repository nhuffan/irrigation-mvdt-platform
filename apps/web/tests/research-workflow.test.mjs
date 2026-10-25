import test from 'node:test';
import assert from 'node:assert/strict';
import {workflowFromResponse,workflowEvidenceHref,workflowExportAlignment} from '../src/lib/research-workflow.ts';
function fixture(){return {schema_version:'METHODOLOGY-WORKFLOW-v1',generated_at:'2026-10-25T00:00:00Z',reservoir_ids:['site'],dataset_version:null,state:'DATA_REVIEW_PENDING',compiler_status:'NOT_READY',software_status:'WORKFLOW_READY',research_status:'PENDING',dataset_status:'NOT_FROZEN',steps:['scope','data','functional','evaluation','results'].map(id=>({id,label:id,status:'PENDING',counts:{records:null},blockers:[],evidence:[],next_action:'Supply genuine evidence'})),acceptance:[],approvals:[],fingerprints:{scope:null},metrics:{status:'NOT_COLLECTED',dataset_version:null,snapshot_sha256:null,observation_count:null,coverage:[],rows:[],retrieval:[],paired_time:[],questionnaire:[]}};}
test('missing evidence remains pending independently of a ready workflow',()=>{
 const r=workflowFromResponse(fixture(),'site');assert.equal(r.status,'AVAILABLE');assert.equal(r.data.research_status,'PENDING');assert.equal(r.data.software_status,'WORKFLOW_READY');assert.equal(r.data.metrics.observation_count,null);
});
test('unavailable reads and historical export drift are distinct',()=>{
 assert.equal(workflowExportAlignment(true,true),'LIVE_READBACK_UNAVAILABLE');assert.equal(workflowExportAlignment(false,true),'HISTORICAL_EXPORT_DIFFERS');assert.equal(workflowExportAlignment(false,false),'RECORD_READBACK_MATCH');
});
test('malformed, private and cross-scope responses fail closed',()=>{
 for(const change of [v=>v.schema_version='future',v=>v.reservoir_ids=['other'],v=>v.steps.pop(),v=>v.steps[0].counts.records=-1,v=>v.steps[0].evidence=[{label:'Private',path:'research/dataset/reviewed/a.json',sha256:null}],v=>v.metrics.observation_count='0',v=>v.generated_at='invalid',v=>v.reviewer_name='private']){const v=fixture();change(v);assert.equal(workflowFromResponse(v,'site').status,'UNAVAILABLE');}
});
test('research completion requires all steps and an aligned frozen metric version',()=>{
 const v=fixture();v.research_status='COMPLETE';v.state='RESEARCH_COMPLETE';assert.equal(workflowFromResponse(v,'site').status,'UNAVAILABLE');v.dataset_status='FROZEN';v.dataset_version='synthetic-test-v1';v.metrics.status='APPROVED_FROZEN';v.metrics.dataset_version='synthetic-test-v1';v.metrics.snapshot_sha256='hash';v.steps.forEach(s=>s.status='COMPLETE');assert.equal(workflowFromResponse(v,'site').status,'AVAILABLE');v.metrics.dataset_version='old';assert.equal(workflowFromResponse(v,'site').status,'UNAVAILABLE');
});
test('evidence links permit only public protocols, scripts and empty templates',()=>{
 assert.ok(workflowEvidenceHref('research/evaluation/templates/retrieval_observations.csv'));assert.ok(workflowEvidenceHref('research/dataset/maim_review.template.csv'));for(const path of ['/Users/private.pdf','research/dataset/reviewed/approval.json','research/evaluation/evidence/a.json','https://outside.test/a','research/evaluation/templates/../private.csv']) assert.equal(workflowEvidenceHref(path),null);
});

test('aggregate payloads and contradictory completion states cannot enter the UI',()=>{for(const change of [v=>v.metrics.retrieval=[null],v=>v.metrics.paired_time=[{}],v=>v.metrics.questionnaire=[{question:'Q1',participant_group:'test',n:-1,missing:0,na:0,mean:6,median:null,min:null,max:null,sample_std_dev:null}],v=>v.state='RESEARCH_COMPLETE',v=>v.metrics.rows=[{id:'score',label:'Score',numerator:1,denominator:1,value:1,status:'PASS',missing_reason:null,observation_count:1,dataset_version:null}]]){const v=fixture();change(v);assert.equal(workflowFromResponse(v,'site').status,'UNAVAILABLE');}});

test('nullable metric metadata and historical acceptance retain explicit missingness',()=>{const v=fixture();v.metrics.rows=[{id:'pending',label:'Research results',numerator:null,denominator:null,value:null,status:'NOT_COLLECTED',missing_reason:'No approved observations',observation_count:null,dataset_version:null,unit:null,authority:null,verification:null}];v.acceptance=[{id:'F01',label:'Test',recorded_status:'PASS',status:'NOT_TESTED',dataset_version:'old',asset_id:null,missing:['Asset ID'],evidence_count:1,evidence_sha256:['hash'],checked_at:null}];assert.equal(workflowFromResponse(v,'site').status,'AVAILABLE');});

test('stale snapshot versions and checksum failures remain actionable states',()=>{for(const status of ['VERSION_MISMATCH','STALE_SCOPE','HASH_MISMATCH']){const v=fixture();v.dataset_status=status;v.steps[1].status='STALE';const result=workflowFromResponse(v,'site');assert.equal(result.status,'AVAILABLE');assert.equal(result.data.dataset_status,status);assert.equal(result.data.research_status,'PENDING');}});

// Render the actual view with synthetic transport fixtures; no study data is created.
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const require = createRequire(import.meta.url);
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const compiledView = ts.transpileModule(readFileSync(new URL('../src/components/methodology/methodology-workflow-view.tsx',import.meta.url),'utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS}}).outputText;
function renderView(workflow, hash='') {
 const exports={};
 const dependencies={
  react:{...React,useSyncExternalStore:()=>hash},
  '@/lib/research-workflow':{workflowEvidenceHref},
  './methodology-workflow.module.css':{default:{}},
  '@/components/documents/document-link':{OriginLink:({href,children})=>React.createElement('a',{href},children)},
 };
 vm.runInNewContext(compiledView,{exports,require:id=>dependencies[id]??require(id)});
 return renderToStaticMarkup(React.createElement(exports.MethodologyWorkflowView,{workflow}));
}
test('view opens the first incomplete step and identifies the accepted researcher scope',()=>{
 const v=fixture();v.steps[0].status='COMPLETE';v.approvals=[{type:'RESEARCHER_APPROVAL',scope:'METHODOLOGY_PACKAGE',status:'APPROVED'},{type:'DOMAIN_REVIEW',scope:'MAIM',status:'PENDING'}];
 const html=renderView(v);assert.match(html,/id="research-data"/);assert.match(html,/Software workflow:.*Complete/);assert.match(html,/Research evidence:.*Pending/);assert.match(html,/Researcher approval/);assert.match(html,/Methodology package/);assert.match(html,/Domain review/);assert.match(html,/NOT_FROZEN/);
});
test('hash transitions select exactly one research step while preserving all navigation targets',()=>{
 for(const id of ['scope','data','functional','evaluation','results']){const html=renderView(fixture(),'#research-'+id);assert.match(html,new RegExp('id="research-'+id+'"'));assert.equal((html.match(/aria-current="step"/g)||[]).length,1);assert.equal((html.match(/href="#research-/g)||[]).length,5);}
});
test('results view shows uncollected measurements as unavailable without a fabricated result',()=>{
 const v=fixture();v.metrics.rows=[{id:'pending',label:'Approved research results',numerator:null,denominator:null,value:null,status:'NOT_COLLECTED',missing_reason:'Actual observations required',observation_count:null,dataset_version:null}];
 const html=renderView(v,'#research-results');assert.match(html,/NOT_COLLECTED/);assert.match(html,/Actual observations required/);assert.match(html,/Not collected/);assert.doesNotMatch(html,/Retrieval outcomes and failures|Paired time comparison and exclusions/);
});
test('functional view retains a failed outcome and unsupported historical PASS separately',()=>{
 const v=fixture();v.acceptance=[{id:'F02',label:'Geometry',recorded_status:'FAIL',status:'FAIL',dataset_version:'test',asset_id:null,missing:['Asset ID'],evidence_count:1,evidence_sha256:['hash'],checked_at:null},{id:'F01',label:'GIS',recorded_status:'PASS',status:'NOT_TESTED',dataset_version:'test',asset_id:null,missing:['Asset ID'],evidence_count:1,evidence_sha256:['hash'],checked_at:null}];
 const html=renderView(v,'#research-functional');assert.match(html,/NOT_TESTED/);assert.match(html,/Recorded: PASS/);assert.match(html,/FAIL/);assert.match(html,/Asset ID/);
});

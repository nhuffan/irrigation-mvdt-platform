import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
const require=createRequire(import.meta.url);
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
function load(relative,dependencies={}){
 const source=readFileSync(new URL(relative,import.meta.url),'utf8');
 const compiled=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS}}).outputText;
 const exports={};vm.runInNewContext(compiled,{exports,require:id=>dependencies[id]??require(id)});return exports;
}
const ui={
 PanelSection:({title,description,children})=>React.createElement('section',null,React.createElement('h2',null,title),description&&React.createElement('p',null,description),children),
 MetricCard:({label,value,note})=>React.createElement('div',{'data-metric':label},React.createElement('span',null,label),React.createElement('strong',null,value),React.createElement('small',null,note)),
};
const {MethodologyOverview}=load('../src/components/methodology/methodology-overview.tsx',{
 '@/components/documents/document-link':{OriginLink:({href,returnAnchor,children})=>React.createElement('a',{href,'data-origin':returnAnchor},children)},
 '@/components/ui/panel-section':ui,'@/lib/site-scope':{RESERVOIR_HREF:'/reservoirs/synthetic-site'},'./methodology-overview.module.css':{default:{}},
});
function summary(){return {rows:[{id:'asset',parent_id:null,direct_l2:7,links:1,location:'REFERENCE_LOCATION'},{id:'child',parent_id:'asset',direct_l2:2,links:0,location:'NO_LOCATION'}],totals:{all:2,primary:1,components:1,all_l2:9,verified_om:0,reference_points:1},sources:[{id:'source',link_available:true,live_document_records:1}],unique_linked_documents:1,read_at:'2026-10-25T00:00:00Z',workflow:{status:'AVAILABLE',data:{research_status:'PENDING',compiler_status:'NOT_READY',dataset_status:'NOT_FROZEN'}},controlled:{assets:Array(999)}};}
const render=s=>renderToStaticMarkup(React.createElement(MethodologyOverview,{summary:s}));
function metric(html,label){return html.split('data-metric="'+label.replaceAll('&','&amp;')+'">')[1]?.split('</div>')[0]??'';}
test('overview uses live counts and distinguishes software completion from pending research',()=>{
 const html=render(summary());assert.match(metric(html,'Research assets'),/<strong>2<\/strong>/);assert.doesNotMatch(html,/999/);assert.match(html,/Phase 1 prototype: software complete/);assert.match(html,/Research acceptance: Pending/);assert.match(html,/NOT_READY.*NOT_FROZEN/);assert.match(metric(html,'Verified O&M events'),/<strong>0<\/strong>/);assert.match(html,/Metadata hashes; retained bytes require original checks/);
});
test('unavailable APIs stay unknown rather than becoming missing or zero observations',()=>{
 const s=summary();s.rows[0].location='UNKNOWN';s.rows[0].links=null;s.totals.reference_points=null;s.totals.all_l2=null;s.totals.verified_om=null;s.unique_linked_documents=null;s.workflow={status:'UNAVAILABLE',data:null};const html=render(s);
 for(const label of ['Reference locations','Representative 3D links','Reviewed L2 records','Distinct linked PDFs','Verified O&M events'])assert.match(metric(html,label),/Unavailable/);
 assert.match(html,/Location coverage unavailable/);assert.match(metric(html,'Verified O&M events'),/Event readback unavailable/);assert.doesNotMatch(metric(html,'Verified O&M events'),/No verified event evidence/);assert.doesNotMatch(metric(html,'Reference locations'),/without location|<strong>0/);assert.match(html,/Research acceptance: unavailable/);
});
test('framework keeps six usable origin-aware navigation links and unavailable routes honest',()=>{
 const html=render(summary());for(const route of ['/reservoirs/synthetic-site#assets','/reservoirs/synthetic-site#asset-gis','/reservoirs/synthetic-site/3d','/assets/asset','/data-sources/source/documents','/ai-research-preview'])assert.ok(html.includes('href="'+route+'"'));assert.equal((html.match(/data-origin="methodology-framework"/g)||[]).length,6);
 const s=summary();s.rows=[];s.sources=[];const empty=render(s);assert.match(empty,/Open Asset Detail: unavailable/);assert.match(empty,/Open Documents: unavailable/);assert.doesNotMatch(empty,/href="\/assets\/undefined|href="\/data-sources\/undefined/);
});
function disclosure(hash,retained=false){
 const hooks={...React,useEffect:()=>{},useSyncExternalStore:()=>hash,useState:()=>[null,()=>{}]};
 const {MethodologyDisclosure,methodologyAnchorTarget}=load('../src/components/methodology/methodology-disclosure.tsx',{react:hooks});
 return {html:renderToStaticMarkup(React.createElement(MethodologyDisclosure,{title:'Advanced',retained},'Research tools')),target:methodologyAnchorTarget(hash)};
}
test('advanced workflow is collapsed by default and opens for retained workflow deep links',()=>{
 assert.doesNotMatch(disclosure('').html,/<details[^>]* open/);assert.doesNotMatch(disclosure('#methodology-framework').html,/<details[^>]* open/);assert.doesNotMatch(disclosure('#methodology-evidence').html,/<details[^>]* open/);
 for(const id of ['scope','data','functional','evaluation','results']){const view=disclosure('#research-'+id);assert.equal(view.target,'workflow');assert.match(view.html,/<details[^>]* open/);assert.doesNotMatch(disclosure('#research-'+id,true).html,/<details[^>]* open/);}
});
test('legacy coverage links open both disclosures without promoting invalid fragments',()=>{
 for(const hash of ['#coverage','#scope','#evaluation','#protocol','#methodology-asset-RS-DT-DAM','#source-age-basis']){assert.equal(disclosure(hash).target,'retained');assert.match(disclosure(hash).html,/<details[^>]* open/);assert.match(disclosure(hash,true).html,/<details[^>]* open/);}
 for(const hash of ['#research-future','#%E0%A4%A','#unrelated']){assert.equal(disclosure(hash).target,null);assert.doesNotMatch(disclosure(hash).html,/<details[^>]* open/);}
});

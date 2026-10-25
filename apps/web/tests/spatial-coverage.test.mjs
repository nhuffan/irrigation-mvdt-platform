import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import {assetLocation, mapGeometry, spatialDisposition, spatialCoverage, locationMatches, pointGroups, pointNeighbors, hierarchy} from '../src/lib/asset-location.ts';
import {publicAssets} from '../src/lib/public-client-data.ts';
import {locationEvidence, locationSource} from '../src/lib/location-evidence.ts';
import {explorerFilters} from '../src/lib/explorer-state.ts';
import {evidenceDisplayText} from '../src/lib/evidence-display.ts';
const require=createRequire(import.meta.url), ts=require('typescript'), React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const base={id:'asset',reservoir_id:'reservoir',asset_code:'RS-TEST',name:'Asset',parent_asset_id:null,category:{code:'INTAKE',name:'Intake'},geometry:null};
const location={location_status:'NO_LOCATION',geometry:null,geometry_type:null,source:null,locator:null,crs:null,evidence_id:null,reviewer:null,reviewed_at:null,review_state:'PENDING',accuracy_limitation:'Unknown',verification_note:'No reviewed point'};
function asset(id,disposition='NO_DEFENSIBLE_LOCATION',extra={}){return {...base,id,name:id,location:{...location,spatial_disposition:disposition,...extra}};}
function reference(id,point=[106.3,11.3]){return asset(id,'REFERENCE_LOCATION',{location_status:'REFERENCE_LOCATION',review_state:'AVAILABLE',geometry:{type:'Point',coordinates:point},reviewed_at:'2026-10-25',evidence_id:'test',source:'Public map',crs:'EPSG:4326'});}
const candidate=()=>asset('candidate','CANDIDATE_NEEDS_REVIEW',{candidate_count:1,reason:'Identity is unconfirmed',next_action:'Review canal crosswalk',candidates:[{candidate_id:'candidate-1',source_label:'Culvert No. 1',source:'Original report',source_url:'https://example.org/report.pdf',document_id:null,physical_page:22,locator:'PDF:p22:Table2.1',coordinate_basis:'Source-reported',source_crs:'Unspecified',identity_basis:'Canal unconfirmed',accuracy_limitation:'Unknown',issues:['IDENTITY_UNCONFIRMED'],coordinates:[106.34,11.32],receipt:'/Users/private/receipt.json'}]});

test('candidate and conflicted geometry remain absent from map while status/reason stay inspectable',()=>{
 for(const disposition of ['CANDIDATE_NEEDS_REVIEW','CONFLICTED','NO_DEFENSIBLE_LOCATION']){
  const a=asset('a',disposition,{geometry:{type:'Point',coordinates:[106,11]}});
  assert.equal(mapGeometry(a),null);assert.equal(spatialDisposition(a),disposition);
 }
 assert.equal(mapGeometry({...base,location:{...location,location_status:'FUTURE_STATE',geometry:{type:'Point',coordinates:[106,11]}}}),null);
 const shown=publicAssets([candidate()])[0];assert.equal(shown.location.geometry,null);assert.equal(shown.location.candidates[0].physical_page,22);
 assert.equal(shown.location.reason,'Identity is unconfirmed');assert.equal(shown.location.candidates[0].coordinates,undefined);assert.equal(shown.location.candidates[0].receipt,undefined);
 assert.doesNotMatch(JSON.stringify(shown),/106.34|11.32|private\/receipt/);
});
test('coverage categories are disjoint, evidence-backed and do not inherit parent points',()=>{
 const parent=asset('parent'), child=reference('child'), missing=asset('missing'), conflict=asset('conflict','CONFLICTED');child.parent_asset_id=parent.id;
 const all=[parent,child,candidate(),missing,conflict,asset('verified','VERIFIED_GEOMETRY',{location_status:'VERIFIED_GEOMETRY',review_state:'AVAILABLE',geometry:{type:'Point',coordinates:[106,11]}})];
 assert.deepEqual(spatialCoverage(all),{reference:1,verified:1,unresolved:2,missing:2,unavailable:0,total:6});
 assert.equal(mapGeometry(parent),null);assert.deepEqual(hierarchy(all,parent).children,[child]);
 assert.equal(spatialCoverage([{...base}]).unavailable,1);
 assert.equal(spatialCoverage([asset('unavailable','NO_DEFENSIBLE_LOCATION',{review_state:'UNAVAILABLE'})]).unavailable,1);
});
test('candidate and missing filters restore from URL without broadening geometry scope',()=>{
 const a=candidate(), conflict=asset('conflict','CONFLICTED'), absent=asset('missing'), mapped=reference('reference');
 assert.ok(locationMatches(a,'UNRESOLVED'));assert.ok(locationMatches(conflict,'UNRESOLVED'));assert.ok(!locationMatches(absent,'UNRESOLVED'));
 assert.ok(locationMatches(a,'NO_LOCATION'));assert.ok(!locationMatches(a,'NO_DEFENSIBLE_LOCATION'));assert.ok(locationMatches(absent,'NO_DEFENSIBLE_LOCATION'));assert.ok(!locationMatches(mapped,'NO_LOCATION'));
 for(const filter of ['UNRESOLVED','CANDIDATE_NEEDS_REVIEW','CONFLICTED','NO_DEFENSIBLE_LOCATION'])assert.equal(explorerFilters(new URLSearchParams({location:filter})).location,filter);
 assert.equal(explorerFilters(new URLSearchParams({location:'INVENTED'})).location,'all');
});
test('co-located accepted assets share a marker and retain exact IDs and source coordinates',()=>{
 const first=reference('first'),second=reference('second'),third=reference('third',[106.31,11.31]),unapproved=candidate();
 const all=[first,second,third,unapproved],before=JSON.stringify(all);
 assert.deepEqual(pointGroups(all),[[first,second],[third]]);
 const project=point=>({x:point[0]*10000,y:point[1]*10000});
 assert.deepEqual(pointNeighbors(all,'first',project),[first,second]);
 assert.deepEqual(pointNeighbors(all,'third',project),[third]);
 assert.deepEqual(pointNeighbors(all,'unavailable',project),[]);
 assert.equal(JSON.stringify(all),before);
});
test('popup evidence exposes provenance/review/unknown accuracy with source-page links and no reviewer identity',()=>{
 const a=reference('a');Object.assign(a.location,{document_id:'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',physical_page:22,locator:'PDF:p22:Table2.1',coordinate_basis:'Source-reported',reviewer_role:'RESEARCHER',reviewer:'Private person'});
 const shown=locationEvidence(a);assert.equal(shown.href,'/documents/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee?page=22');
 assert.deepEqual(shown.fields.find(([label])=>label==='Estimated accuracy'),['Estimated accuracy','Unknown']);
 assert.ok(shown.fields.find(([label,value])=>label==='Review'&&value.includes('Accepted · RESEARCHER')));
 assert.doesNotMatch(JSON.stringify(shown),/Private person/);
 a.location.document_id='bad';a.location.source_url='file:///Users/private/map.pdf';assert.equal(locationEvidence(a).href,null);
});
function load(relative,dependencies={}){const source=readFileSync(new URL(relative,import.meta.url),'utf8');const compiled=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS}}).outputText;const exports={};vm.runInNewContext(compiled,{exports,requestAnimationFrame:()=>{},require:id=>dependencies[id]??require(id)});return exports;}
const shared={
 '@/lib/evidence-display':{evidenceDisplayText},
 '@/lib/asset-location':{assetLocation,spatialCoverage,hierarchy},
 '@/lib/location-evidence':{locationSource},
 '@/lib/asset-display':{assetDisplayName:a=>a.name,locationSourceTitle:s=>s??'Unknown'},
 '@/components/documents/document-link':{OriginLink:({href,children})=>React.createElement('a',{href},children)},
 '@/lib/asset-information':{publicEvidenceHref:s=>s??null,publicEvidenceText:s=>s??'Unknown'},
 './presentation':{TechnicalMetadataPopover:({fields})=>React.createElement('dl',null,Object.entries(fields).map(([key,value])=>React.createElement('div',{key},key+': '+value)))},
 './spatial-coverage.module.css':{default:{}},
};
const {LocationBadge}=load('../src/components/asset/location-badge.tsx',{'@/lib/asset-location':{spatialDisposition},'./spatial-coverage.module.css':{default:{}}});
const {AssetLocationSummary}=load('../src/components/asset/asset-location-summary.tsx',{...shared,'./location-badge':{LocationBadge}});
const {SpatialCoverage}=load('../src/components/asset/spatial-coverage.tsx',{...shared,'./location-badge':{LocationBadge},'./asset-location-summary':{AssetLocationSummary}});
const render=assets=>renderToStaticMarkup(React.createElement(SpatialCoverage,{assets}));
test('coverage is useful without pins: all identities, review reasons and source evidence are discoverable',()=>{
 const a=candidate(), html=render([reference('reference'),a,asset('missing')]);
 for(const phrase of ['Accepted references','Verified geometries','Unresolved candidates','No location','Evidence and unresolved locations','Identity is unconfirmed','Review canal crosswalk','Culvert No. 1','PDF page 22'])assert.ok(html.includes(phrase),phrase);
 assert.match(html,/href="\/reservoirs\/reservoir\?asset=candidate#asset-gis"/);assert.match(html,/CANDIDATE NEEDS REVIEW/);
 assert.doesNotMatch(html,/106.34|11.32|id="location"/);
 const unknown=render([{...base}]);assert.equal((unknown.match(/<strong>Unavailable<\/strong>/g)||[]).length,4);assert.match(unknown,/Coverage totals cannot be confirmed/);
});

test('coverage filter buttons toggle exactly one preserved state and inspection keeps asset identity',()=>{
 function descendants(node){if(!node||typeof node!=='object')return [];return [node,...React.Children.toArray(node.props?.children).flatMap(descendants)];}
 const all=[reference('reference'),candidate(),asset('missing')], changes=[];
 let tree=SpatialCoverage({assets:all,onFilter:value=>changes.push(value),activeFilter:'all'});
 const buttons=descendants(tree).filter(node=>node.type==='button');
 assert.equal(buttons.length,4);buttons[2].props.onClick();assert.deepEqual(changes,['UNRESOLVED']);
 tree=SpatialCoverage({assets:all,onFilter:value=>changes.push(value),activeFilter:'UNRESOLVED'});
 const active=descendants(tree).find(node=>node.type==='button'&&node.props['aria-pressed']);assert.ok(active);active.props.onClick();assert.deepEqual(changes,['UNRESOLVED','all']);
 const selected=[];tree=SpatialCoverage({assets:all,onSelect:value=>selected.push(value)});
 const inspect=descendants(tree).find(node=>node.type==='button'&&node.props['aria-label']==='Inspect candidate');assert.ok(inspect);inspect.props.onClick();assert.equal(selected[0],all[1]);
});
test('source links reject invalid IDs/pages and never infer a page or CRS from candidate evidence',()=>{
 assert.deepEqual(locationSource({document_id:'invalid',physical_page:-5,source_url:'https://example.org/source.pdf'}),{href:'https://example.org/source.pdf',page:null});
 assert.equal(locationSource({document_id:'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',physical_page:1.5}).href,'/documents/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee');
 const accepted=reference('old');accepted.location.locator='PDF:p22:Table2.1';accepted.location.candidates=candidate().location.candidates;
 assert.equal(locationEvidence(accepted).page,null);assert.deepEqual(locationEvidence(accepted).fields.find(([key])=>key==='Coordinate basis'),['Coordinate basis','Unknown']);
 for(const state of [{...reference('bad').location,geometry:null},{...reference('bad').location,review_state:'PENDING'},{...location,location_status:'UNKNOWN'}])assert.equal(spatialCoverage([{...base,location:state}]).unavailable,1);
});

test('candidate client metadata rejects local/keyed URLs and private fields without dropping source identities',()=>{
 for(const href of ['file:///Users/private/source.pdf','http://127.0.0.1/source.pdf','https://example.org/source.pdf?token=private','https://user:password@example.org/source.pdf']){
  const a=candidate();Object.assign(a.location.candidates[0],{source_url:href,reviewer:'Private Reviewer',original_path:'/Users/private/report.pdf'});
  const shown=publicAssets([a])[0].location.candidates[0];assert.equal(shown.source_url,null);assert.equal(shown.source_label,'Culvert No. 1');assert.equal(shown.reviewer,undefined);assert.equal(shown.original_path,undefined);
 }
});

test('actual shared-marker click offers every identity and selection opens its exact unchanged point',async()=>{
 class Element {
  constructor(tag){this.tag=tag;this.children=[];this.attributes={};this.dataset={};this.events={};this.classList={toggle:()=>{}};}
  append(...nodes){this.children.push(...nodes);}setAttribute(key,value){this.attributes[key]=value;}addEventListener(name,callback){this.events[name]=callback;}
 }
 const markers=[],popups=[],maps=[],effects=[],selections=[];let refIndex=0;
 class Map {
  constructor(){this.events={};this.layers=[];this.sources={};maps.push(this);}
  on(name,callback){(this.events[name]??=[]).push(callback);}addControl(){}resize(){}jumpTo(){}flyTo(){}
  addSource(name,value){this.sources[name]=value;}addLayer(value){this.layers.push(value);}getStyle(){return {layers:this.layers};}removeLayer(id){this.layers=this.layers.filter(layer=>layer.id!==id);}
  setFeatureState(){}getContainer(){return {clientWidth:600};}fitBounds(bounds){this.lastBounds=bounds;}project(point){return {x:point[0]*10000,y:point[1]*10000};}
  getCenter(){return {lng:106.3,lat:11.3};}getZoom(){return 11;}getBearing(){return 0;}getPitch(){return 0;}loaded(){return true;}
 }
 class Marker {constructor({element}){this.element=element;markers.push(this);}setLngLat(point){this.point=point;return this;}addTo(){return this;}}
 class Popup {constructor(){popups.push(this);}setLngLat(point){this.point=point;return this;}setDOMContent(element){this.element=element;return this;}addTo(){return this;}remove(){}}
 class Bounds {constructor(){this.points=[];}extend(point){this.points.push(point);}getCenter(){return this.points[0];}}
 const hooks={...React,useRef:initial=>({current:refIndex++===2?{clientWidth:600}:initial}),useEffect:callback=>effects.push(callback),useState:initial=>[initial,()=>{}]};
 const dependencies={
  react:hooks,'@/lib/document-navigation':{documentHref:href=>href},
  '@/lib/workspace-view-state':{mapView:()=>{},readView:()=>null,saveView:()=>{},viewStorage:()=>null},
  '@/lib/workspace-layout':{observeCanvasResize:()=>()=>{}},'@/components/asset/asset-symbol':{AssetSymbol:()=>null},
  '@/lib/asset-symbol':{assetSymbolSvg:()=>'<svg></svg>',assetSymbols:{}},'@/lib/asset-display':{assetDisplayName:a=>a.name},
  '@/lib/asset-location':{assetLocation,mapGeometry,locationLayer:()=> 'RS_REFERENCE',pointGroups,pointNeighbors},
  '@/lib/location-evidence':{locationEvidence},'@/lib/asset-geometry':{geometryPositions:g=>[g.coordinates]},
  'maplibre-gl':{Map,Marker,Popup,LngLatBounds:Bounds,NavigationControl:class{},AttributionControl:class{},ScaleControl:class{},setWorkerUrl:()=>{}},
 };
 const source=readFileSync(new URL('../src/components/map/asset-map.tsx',import.meta.url),'utf8');
 const compiled=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS}}).outputText,exports={};
 vm.runInNewContext(compiled,{exports,require:id=>dependencies[id]??require(id),document:{createElement:tag=>new Element(tag)},window:{location:{pathname:'/map',search:'',hash:''}},setTimeout:()=>0,clearTimeout:()=>{},requestAnimationFrame:()=>{}});
 const all=[reference('first'),reference('second'),candidate()];const before=JSON.stringify(all);
 exports.AssetMap({reservoir:{id:'reservoir',name:'Reservoir',longitude:106.3,latitude:11.3},assets:all,onSelect:a=>selections.push(a),contextVisible:false});
 effects.forEach(effect=>effect());await new Promise(resolve=>setImmediate(resolve));
 const map=maps[0];assert.ok(map);map.events.load.forEach(callback=>callback());
 assert.equal(markers.length,1,'one marker represents the exact shared point, candidate gets none');
 assert.equal(JSON.stringify(markers[0].point),JSON.stringify([106.3,11.3]));
 markers[0].element.events.click({stopPropagation(){}});const choices=popups.at(-1).element.children.filter(child=>child.tag==='button');
 assert.equal(choices.length,2);assert.equal(choices[1].textContent,'second');choices[1].events.click();
 assert.equal(selections.at(-1).id,all[1].id);assert.equal(JSON.stringify(selections.at(-1)),JSON.stringify(all[1]));assert.equal(popups.at(-1).element.children[0].textContent,'second');
 assert.equal(JSON.stringify(map.lastBounds.points),JSON.stringify([[106.3,11.3]]));assert.equal(JSON.stringify(all),before);
 assert.equal(map.sources.assets.data.features.length,2,'both accepted identities remain in map data');
});

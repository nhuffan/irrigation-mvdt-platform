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
import {satelliteConfig, STREET_LAYER} from '../src/lib/satellite-provider.ts';
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

function descendants(node){
 if(!node||typeof node!=='object')return [];
 return [node,...React.Children.toArray(node.props?.children).flatMap(descendants)];
}
async function assetMapHarness({configured=true}={}){
 class Element {
  constructor(tag){this.tag=tag;this.children=[];this.attributes={};this.dataset={};this.events={};this.classList={toggle:()=>{}};}
  append(...nodes){this.children.push(...nodes);}remove(){this.removed=true;}setAttribute(key,value){this.attributes[key]=value;}addEventListener(name,callback){this.events[name]=callback;}
 }
 const markers=[],popups=[],maps=[],selections=[],refs=[],states=[],effectSlots=[],timers=new Set();
 const all=[reference('first'),reference('second'),candidate()],before=JSON.stringify(all);
 const reservoir={id:'reservoir',name:'Reservoir',longitude:106.3,latitude:11.3};
 let refIndex=0,stateIndex=0,effectIndex=0,pending=[],tree;
 class Map {
  constructor(options){this.events={};this.layers=[...(options.style.layers??[])];this.sources={};this.loadedSources=new Set();this.cameraMoves=0;maps.push(this);}
  on(name,callback){(this.events[name]??=[]).push(callback);return this;}
  off(name,callback){this.events[name]=(this.events[name]??[]).filter(value=>value!==callback);return this;}
  emit(name,event={}){for(const callback of [...(this.events[name]??[])])callback(event);}
  addControl(control){(this.controls??=[]).push(control);control.onAdd?.();}
  removeControl(control){control.onRemove?.();this.controls=this.controls.filter(value=>value!==control);}
  resize(){}jumpTo(){this.cameraMoves++;}flyTo(){this.cameraMoves++;}
  addSource(name,value){this.sources[name]=value;}
  getSource(name){return this.sources[name];}
  removeSource(name){assert.ok(!this.layers.some(layer=>layer.source===name),'remove basemap layers before their source');delete this.sources[name];}
  addLayer(value,beforeId){const index=this.layers.findIndex(layer=>layer.id===beforeId);if(index===-1)this.layers.push(value);else this.layers.splice(index,0,value);}
  getLayer(id){return this.layers.find(layer=>layer.id===id);}
  getStyle(){return {layers:this.layers,sources:this.sources};}
  removeLayer(id){this.layers=this.layers.filter(layer=>layer.id!==id);}
  isSourceLoaded(id){return this.loadedSources.has(id);}
  setFeatureState(){}getContainer(){return {clientWidth:600};}
  fitBounds(bounds){this.lastBounds=bounds;this.cameraMoves++;}
  project(point){return {x:point[0]*10000,y:point[1]*10000};}
  getCenter(){return {lng:106.3,lat:11.3};}getZoom(){return 11;}getBearing(){return 0;}getPitch(){return 0;}loaded(){return true;}
  remove(){this.removed=true;for(const control of this.controls??[])control.onRemove?.();}
 }
 class Marker {constructor({element}){this.element=element;markers.push(this);}setLngLat(point){this.point=point;return this;}addTo(){return this;}}
 class Popup {constructor(){popups.push(this);}setLngLat(point){this.point=point;return this;}setDOMContent(element){this.element=element;return this;}addTo(){return this;}remove(){}}
 class Bounds {constructor(){this.points=[];}extend(point){this.points.push(point);}getCenter(){return this.points[0];}}
 const hooks={...React,
  useRef:initial=>refs[refIndex++]??(refs[refIndex-1]={current:initial}),
  useEffect:(callback,deps)=>{
   const index=effectIndex++,previous=effectSlots[index];
   if(!previous||!deps||deps.some((value,i)=>!Object.is(value,previous.deps?.[i])))pending.push(()=>{previous?.cleanup?.();effectSlots[index]={deps,cleanup:callback()};});
  },
  useState:initial=>{
   const index=stateIndex++;if(!(index in states))states[index]=initial;
   return [states[index],value=>{states[index]=typeof value==='function'?value(states[index]):value;}];
  },
 };
 const dependencies={
  react:hooks,'@/lib/document-navigation':{documentHref:href=>href},
  '@/lib/workspace-view-state':{mapView:()=>{},readView:()=>null,saveView:()=>{},viewStorage:()=>null},
  '@/lib/workspace-layout':{observeCanvasResize:()=>()=>{}},'@/components/asset/asset-symbol':{AssetSymbol:()=>null},
  '@/lib/asset-symbol':{assetSymbolSvg:()=>'<svg></svg>',assetSymbols:{}},'@/lib/asset-display':{assetDisplayName:a=>a.name},
  '@/lib/asset-location':{assetLocation,mapGeometry,locationLayer:()=> 'RS_REFERENCE',pointGroups,pointNeighbors},
  '@/lib/location-evidence':{locationEvidence},'@/lib/asset-geometry':{geometryPositions:g=>[g.coordinates]},
  '@/lib/satellite-provider':{satelliteConfig,STREET_LAYER},
  'maplibre-gl':{Map,Marker,Popup,LngLatBounds:Bounds,NavigationControl:class{},AttributionControl:class{},ScaleControl:class{},setWorkerUrl:()=>{}},
 };
 const source=readFileSync(new URL('../src/components/map/asset-map.tsx',import.meta.url),'utf8');
 const compiled=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS}}).outputText,exports={};
 vm.runInNewContext(compiled,{exports,require:id=>dependencies[id]??require(id),document:{createElement:tag=>new Element(tag)},window:{location:{pathname:'/map',search:'',hash:''}},
  process:{env:configured?{NEXT_PUBLIC_SATELLITE_PROVIDER:'maptiler',NEXT_PUBLIC_MAPTILER_KEY:'unit_test_asset_map_owner_123'}:{}},
  setTimeout:callback=>{const timer={callback};timers.add(timer);return timer;},clearTimeout:timer=>timers.delete(timer),requestAnimationFrame:()=>{},
 });
 const props={reservoir,assets:all,onSelect:a=>selections.push(a),contextVisible:false};
 function render(){
  refIndex=0;stateIndex=0;effectIndex=0;pending=[];tree=exports.AssetMap(props);
  for(const node of descendants(tree))if(node.props?.className==='asset-map-canvas')node.props.ref.current={clientWidth:600};
  for(const effect of pending)effect();return tree;
 }
 render();await new Promise(resolve=>setImmediate(resolve));
 const map=maps[0];assert.ok(map);map.emit('load');render();
 return {map,maps,markers,popups,selections,all,before,timers,render,
  basemapId:()=>Object.keys(map.sources).find(id=>map.sources[id].type==='raster'),
  retry:()=>{
   const retry=descendants(render()).find(node=>node.type==='button'&&node.props.children==='Retry basemap');
   assert.ok(retry,'failed basemap exposes a focused retry action');retry.props.onClick();
  },
  cleanup:()=>{for(const effect of effectSlots)effect.cleanup?.();},
 };
}

test('actual shared-marker click offers every identity and selection opens its exact unchanged point',async()=>{
 const {map,markers,popups,selections,all,before,cleanup}=await assetMapHarness();
 assert.equal(markers.length,1,'one marker represents the exact shared point, candidate gets none');
 assert.equal(JSON.stringify(markers[0].point),JSON.stringify([106.3,11.3]));
 markers[0].element.events.click({stopPropagation(){}});const choices=popups.at(-1).element.children.filter(child=>child.tag==='button');
 assert.equal(choices.length,2);assert.equal(choices[1].textContent,'second');choices[1].events.click();
 assert.equal(selections.at(-1).id,all[1].id);assert.equal(JSON.stringify(selections.at(-1)),JSON.stringify(all[1]));assert.equal(popups.at(-1).element.children[0].textContent,'second');
 assert.equal(JSON.stringify(map.lastBounds.points),JSON.stringify([[106.3,11.3]]));assert.equal(JSON.stringify(all),before);
 assert.equal(map.sources.assets.data.features.length,2,'both accepted identities remain in map data');cleanup();
});

test('asset basemap prefers the configured owner provider and accepts readiness only for its current source',async()=>{
 const h=await assetMapHarness(),id=h.basemapId(),source=h.map.sources[id];
 assert.match(source.url,/^https:\/\/api\.maptiler\.com\/maps\/streets\/256\/tiles\.json\?key=unit_test_asset_map_owner_123$/);
 assert.equal(source.tileSize,256);assert.match(source.attribution,/MapTiler/);assert.match(source.attribution,/OpenStreetMap contributors/);
 assert.equal(h.timers.size,1,'only the basemap deadline remains after independent asset initialization');
 h.map.emit('sourcedata',{sourceId:'assets',isSourceLoaded:true});assert.equal(h.timers.size,1,'asset readiness cannot claim basemap success');
 h.map.emit('sourcedata',{sourceId:id,isSourceLoaded:false});assert.equal(h.timers.size,1);
 h.map.emit('sourcedata',{sourceId:id,isSourceLoaded:true});assert.equal(h.timers.size,0);
 assert.equal(h.basemapId(),id);assert.equal(h.map.sources.assets.data.features.length,2);assert.equal(JSON.stringify(h.all),h.before);
 h.cleanup();assert.ok(h.map.removed);assert.equal(h.timers.size,0);
 h.map.emit('error',{sourceId:id});assert.equal(h.basemapId(),id,'late errors cannot restart a disposed map');
});

test('failed asset imagery falls back once, removes patchwork and retries without moving or recreating assets',async()=>{
 const h=await assetMapHarness(),preferred=h.basemapId(),assetSource=h.map.sources.assets,moves=h.map.cameraMoves;
 h.map.emit('error',{sourceId:preferred});const fallback=h.basemapId();
 assert.notEqual(fallback,preferred);assert.equal(h.map.sources[preferred],undefined);assert.equal(h.map.getLayer(preferred),undefined);
 assert.equal(JSON.stringify(h.map.sources[fallback].tiles),JSON.stringify(STREET_LAYER.tiles));
 h.map.emit('error',{sourceId:preferred});assert.equal(h.basemapId(),fallback,'stale errors do not replace a newer source');
 h.map.emit('error',{sourceId:fallback});assert.equal(h.basemapId(),undefined,'all failed raster fragments are removed');
 assert.ok(!h.map.layers.some(layer=>layer.type==='raster'));assert.equal(h.map.sources.assets,assetSource);
 assert.equal(h.maps.length,1);assert.equal(h.markers.length,1);assert.equal(h.map.cameraMoves,moves);
 assert.equal(h.timers.size,0,'failed OSM does not loop through automatic retries');
 h.retry();const retried=h.basemapId();assert.notEqual(retried,preferred);assert.notEqual(retried,fallback);
 assert.match(h.map.sources[retried].url,/api\.maptiler\.com/);assert.equal(h.timers.size,1);
 h.map.emit('sourcedata',{sourceId:fallback,isSourceLoaded:true});assert.equal(h.timers.size,1,'late fallback success cannot clear the retry deadline');
 h.map.emit('sourcedata',{sourceId:retried,isSourceLoaded:true});assert.equal(h.timers.size,0);
 assert.ok(!descendants(h.render()).some(node=>node.props?.className==='basemap-notice'),'successful recovery clears the unavailable notice');
 assert.equal(h.map.sources.assets,assetSource);assert.equal(h.map.cameraMoves,moves);assert.equal(h.maps.length,1);assert.equal(h.markers.length,1);
 assert.ok(h.map.layers.findIndex(layer=>layer.id===retried)<h.map.layers.findIndex(layer=>layer.id==='reservoir-context'),'retried basemap remains behind asset/context overlays');
 h.markers[0].element.events.click({stopPropagation(){}});
 const choices=h.popups.at(-1).element.children.filter(child=>child.tag==='button');choices[1].events.click();
 assert.equal(h.selections.at(-1).id,'second');assert.equal(JSON.stringify(h.all),h.before);h.cleanup();
});

test('missing owner configuration uses OSM directly and timeouts leave clean context with a focused retry',async()=>{
 const h=await assetMapHarness({configured:false}),first=h.basemapId();
 assert.equal(h.map.sources[first].url,undefined);assert.equal(JSON.stringify(h.map.sources[first].tiles),JSON.stringify(STREET_LAYER.tiles));
 const timer=[...h.timers][0];h.timers.delete(timer);timer.callback();
 assert.equal(h.basemapId(),undefined);assert.ok(!h.map.layers.some(layer=>layer.type==='raster'));
 const reset=descendants(h.render()).find(node=>node.type==='button'&&node.props.children==='Reset map');assert.equal(reset.props.disabled,false,'asset map remains usable after only basemap failure');
 h.retry();assert.equal(JSON.stringify(h.map.sources[h.basemapId()].tiles),JSON.stringify(STREET_LAYER.tiles));
 h.cleanup();assert.equal(h.timers.size,0);const active=h.basemapId();
 h.map.emit('sourcedata',{sourceId:active,isSourceLoaded:true});h.map.emit('error',{sourceId:active});assert.equal(h.basemapId(),active,'cleanup prevents late source events from adding backgrounds');
});

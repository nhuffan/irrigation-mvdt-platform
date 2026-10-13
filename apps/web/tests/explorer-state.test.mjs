import test from 'node:test';
import assert from 'node:assert/strict';
import { dataset, selectedAsset, filterAssets, recordTotal, reviewedPreview, modelHref } from '../src/lib/explorer-state.ts';
import { geometryPositions } from '../src/lib/asset-geometry.ts';
const rs = {id:'r',asset_code:'RS-A',geometry:null,reservoir_id:'reservoir'};
const dev = {id:'d',asset_code:'DEV-A',geometry:{type:'Point',coordinates:[106,11]}};
const child = {id:'c',asset_code:'RS-C',parent_asset_id:'r',geometry:{type:'LineString',coordinates:[[106,11],[106.1,11.1]]}};
const assets=[rs,dev,child];
const records={r:{technical:[],events:[],links:[{model_id:'model',object_key:'node / 1'}]},d:{technical:[],events:[],links:[]},c:{technical:[],events:[],links:[]}};
test('registry, map and deep-link IDs resolve the same asset without a fallback',()=>{
 for(const a of assets) assert.equal(selectedAsset(assets,a.id),a);
 assert.equal(selectedAsset(assets,'missing'),undefined);
 assert.equal(selectedAsset(assets,null),undefined);
});
test('RS and DEV remain separate; unclassified is not silently research',()=>{
 assert.deepEqual(filterAssets(assets,'research',false,false,records),[rs,child]);
 assert.deepEqual(filterAssets(assets,'development',false,false,records),[dev]);
 assert.equal(dataset({...rs,asset_code:'OTHER'}),'other');
});
test('NULL geometry is excluded; controlled children need no special naming logic',()=>{
 assert.deepEqual(filterAssets(assets,'research',true,false,records),[child]);
 assert.deepEqual(geometryPositions(child.geometry),child.geometry.coordinates);
 assert.deepEqual(geometryPositions(dev.geometry),[[106,11]]);
 assert.deepEqual(geometryPositions({type:'Polygon',coordinates:[[[1,2],[3,4],[1,2]]]}),[[1,2],[3,4],[1,2]]);
});
test('3D actions require actual links and object keys are encoded',()=>{
 assert.deepEqual(filterAssets(assets,'research',false,true,records),[rs]);
 assert.equal(modelHref(rs,records.r.links[0]),'/reservoirs/reservoir/3d?model=model&object=node%20%2F%201');
});
test('zero verified events differs from unknown API data',()=>{
 assert.equal(recordTotal([rs],records,'events'),0);
 assert.equal(recordTotal([rs],{r:{events:null}},'events'),null);
 assert.equal(recordTotal([rs],{},'events'),null);
});
test('preview preserves reviewed L2 and never infers it from VERIFIED',()=>{
 const item={verification_status:'VERIFIED',reviewed_provenance:{verification_level:'L2',source_code:'source',authority:'SUPPORTING'}};
 assert.deepEqual(reviewedPreview({technical:[{verification_status:'VERIFIED'},item,item,item,item]}),[item,item,item]);
 assert.equal(reviewedPreview({technical:null}),undefined);
 assert.equal(item.reviewed_provenance.verification_level,'L2');
});
test('presentation query does not participate in filtering or counts',()=>{
 const original=JSON.stringify({assets,records});
 for(const paper of ['0','1']) {
  const params=new URLSearchParams({asset:'r',paper});
  assert.equal(selectedAsset(assets,params.get('asset')),rs);
  assert.equal(recordTotal(filterAssets(assets,'research',false,false,records),records,'links'),1);
 }
 assert.equal(JSON.stringify({assets,records}),original);
});

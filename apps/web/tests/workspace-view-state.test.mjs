import test from 'node:test';
import assert from 'node:assert/strict';
import { mapView, cameraView, readView, saveView, scopedSnapshot } from '../src/lib/workspace-view-state.ts';
import { explorerFilters, explorerFilterUrl } from '../src/lib/explorer-state.ts';
import { referenceNeighbors } from '../src/lib/observation-map.ts';

const map = { center: [106.34,11.32], zoom: 10, bearing: 12, pitch: 20 };
const camera = { position: [120,80,45], direction: [0,0,-1], up: [0,1,0] };

test('only bounded numeric map/camera preferences survive storage validation', () => {
  assert.deepEqual(mapView({ ...map, evidence: 'must not persist' }), map);
  assert.deepEqual(cameraView({ ...camera, citations: [{ text: 'must not persist' }] }), camera);
  for (const patch of [{center:[181,10]},{center:[106,91]},{zoom:Infinity},{zoom:25},{pitch:90},{bearing:-361}]) assert.equal(mapView({...map,...patch}),null);
  for (const patch of [{position:[NaN,0,0]},{position:[1e10,0,0]},{direction:[0,0,0]},{up:[0,0,-1]},{up:[0,2,0]}]) assert.equal(cameraView({...camera,...patch}),null);
});

test('view storage ignores invalid, future, expired and unavailable snapshots without blocking rendering', () => {
  const rows = new Map();
  const storage = { getItem: key => rows.get(key) ?? null, setItem: (key,value) => rows.set(key,value) };
  saveView(storage,'asset:one',map);
  assert.deepEqual(readView(storage,'asset:one',mapView),map);
  assert.equal(readView(storage,'asset:two',mapView),null);
  const serialized = JSON.parse(rows.get('mvdt:view:asset:one'));
  assert.deepEqual(Object.keys(serialized).sort(),['savedAt','version','view']);
  for (const value of [
    '{invalid', JSON.stringify({...serialized,version:2}),
    JSON.stringify({...serialized,savedAt:Date.now()+60000}),
    JSON.stringify({...serialized,savedAt:Date.now()-86400001}),
    JSON.stringify({...serialized,view:{...map,center:['106',11]}}),
  ]) { rows.set('mvdt:view:asset:one',value); assert.equal(readView(storage,'asset:one',mapView),null); }
  const blocked = { getItem: () => { throw Error('blocked'); }, setItem: () => { throw Error('full'); } };
  assert.equal(readView(blocked,'one',mapView),null);
  assert.doesNotThrow(()=>saveView(blocked,'one',camera));
});

test('an old request payload cannot render under a newly selected asset', () => {
  const old = { id:'asset-a', data:[{status:'fulfilled',value:{id:'asset-a'}}] };
  assert.equal(scopedSnapshot(old,'asset-b'),null);
  assert.equal(scopedSnapshot(null,'asset-b'),null);
  const latest = { id:'asset-b', data:[{status:'fulfilled',value:{id:'asset-b'}},{status:'rejected',reason:Error('offline')}] };
  assert.equal(scopedSnapshot(latest,'asset-b'),latest.data);
  // Partial failures stay explicit; valid identity does not become empty data.
  assert.equal(scopedSnapshot(latest,'asset-b')[1].status,'rejected');
  assert.equal(scopedSnapshot(old,'asset-b'),null);
});

test('explorer filter changes preserve selected asset, origin and anchor across Back/reload', () => {
  const href='https://app.invalid/reservoirs/reservoir?asset=component&returnTo=%2Fmap#asset-gis';
  let url=explorerFilterUrl(href,'q','Cống số 3');
  url=explorerFilterUrl(new URL(url,'https://app.invalid').href,'location','NO_LOCATION');
  url=explorerFilterUrl(new URL(url,'https://app.invalid').href,'modelOnly','1');
  const parsed=new URL(url,'https://app.invalid');
  assert.equal(parsed.searchParams.get('asset'),'component');
  assert.equal(parsed.searchParams.get('returnTo'),'/map');
  assert.equal(parsed.hash,'#asset-gis');
  assert.deepEqual(explorerFilters(parsed.searchParams),{query:'Cống số 3',type:'',location:'NO_LOCATION',contextVisible:true,modelOnly:true});
  assert.equal(explorerFilters(new URLSearchParams('location=unknown')).location,'all');
  assert.equal(explorerFilters(new URLSearchParams({q:'x'.repeat(250)})).query.length,200);
});

function reference(id,coordinates) {
  return {id,location:{location_status:'REFERENCE_LOCATION',review_state:'AVAILABLE',reviewed_at:'2026-01-01',evidence_id:'reviewed',crs:'EPSG:4326',geometry:{type:'Point',coordinates}}};
}
test('overlapping regional markers expose every exact source asset without moving coordinates', () => {
  const assets=[reference('dam',[106.340773,11.323022]),reference('spillway',[106.34876,11.32473]),reference('distant',[107,12])];
  const original=JSON.stringify(assets);
  const project=scale=>([lon,lat])=>({x:lon*scale,y:lat*scale});
  assert.deepEqual(referenceNeighbors(assets,'dam',project(1000)).map(a=>a.id),['dam','spillway']);
  assert.deepEqual(referenceNeighbors(assets,'spillway',project(1000)).map(a=>a.id),['dam','spillway']);
  assert.deepEqual(referenceNeighbors(assets,'dam',project(100000)).map(a=>a.id),['dam']);
  assert.deepEqual(referenceNeighbors(assets,'missing',project(1000)),[]);
  assert.equal(JSON.stringify(assets),original);
});

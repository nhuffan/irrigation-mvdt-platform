import test from 'node:test';
import assert from 'node:assert/strict';
import { assetLocation, mapGeometry, locationLayer, hierarchy, matchesSearch } from '../src/lib/asset-location.ts';
const missing={id:'a',asset_code:'RS-A',name:'Tràn tham khảo',category:{code:'SPILLWAY',name:'Spillway'},geometry:null,parent_asset_id:null};
test('reviewed reference uses overlay while canonical geometry stays NULL',()=>{
 const a={...missing,location:{location_status:'REFERENCE_LOCATION',geometry:{type:'Point',coordinates:[106,11]}}};
 assert.equal(a.geometry,null);assert.equal(mapGeometry(a),a.location.geometry);assert.equal(locationLayer(a),'RS_REFERENCE');
 assert.equal(mapGeometry(missing),null);
 assert.equal(assetLocation({...missing,geometry:a.location.geometry}).location_status,'REFERENCE_LOCATION');
});
test('DEV geometry never enters RS verified layer',()=>{
 const a={...missing,asset_code:'DEV-A',location:{location_status:'VERIFIED_GEOMETRY',geometry:{type:'Point',coordinates:[106,11]}}};
 assert.equal(locationLayer(a),'DEV');
});
test('search supports name without accents, code, UUID and category',()=>{
 for(const q of ['tran','RS-A','a','spillway']) assert.equal(matchesSearch(missing,q,''),true);
 assert.equal(matchesSearch(missing,'tran','DAM'),false);
 assert.equal(matchesSearch(missing,'absent',''),false);
});
test('generic hierarchy resolves ancestors and children and terminates cycles',()=>{
 const b={...missing,id:'b',parent_asset_id:'a'}, c={...missing,id:'c',parent_asset_id:'b'};
 assert.deepEqual(hierarchy([missing,b,c],b),{ancestors:[missing],children:[c]});
 assert.equal(hierarchy([{...missing,parent_asset_id:'b'},b],b).ancestors.length,1);
});

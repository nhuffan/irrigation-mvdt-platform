import test from 'node:test';
import assert from 'node:assert/strict';
import { selectedPrimitives } from '../src/lib/model-selection.ts';
import { assetSymbol, assetSymbols, assetSymbolSvg } from '../src/lib/asset-symbol.ts';
const node={node:{name:'roof'}};
const pick=(n=node,id='m')=>({color:{red:1},object:{id,detail:{node:n}}});
test('unique node selects all its primitives, never other objects/models',()=>{
 const a=pick(),b=pick(),other=pick({node:{name:'tree'}}),foreign=pick(node,'other');
 assert.deepEqual(selectedPrimitives({_pickIds:[a,b,other,foreign]},'m','roof'),[a,b]);
 assert.deepEqual(selectedPrimitives({_pickIds:[a]},'m',null),[]);
});
test('duplicate names, instances and unsupported runtime fail closed',()=>{
 assert.deepEqual(selectedPrimitives({_pickIds:[pick(),pick({node:{name:'roof'}})]},'m','roof'),[]);
 const p=pick();p.object.instanceId=0;
 assert.deepEqual(selectedPrimitives({_pickIds:[p]},'m','roof'),[]);
 assert.deepEqual(selectedPrimitives({},'m','roof'),[]);
});
test('four categories have distinct safe symbols, including RS aliases',()=>{
 assert.equal(new Set(Object.values(assetSymbols).map(x=>x.path)).size,4);
 assert.equal(assetSymbol('RS-CAT-INTAKE_SLUICE'),assetSymbols.INTAKE);
 assert.equal(assetSymbol('RS-CAT-MANAGEMENT_BUILDING'),assetSymbols.MGMT);
 assert.match(assetSymbolSvg('SPILLWAY'),/<svg/);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {workspaceLayout,observeCanvasResize} from '../src/lib/workspace-layout.ts';
import {modelSelectionUrl} from '../src/lib/model-deep-link.ts';
test('expand/collapse and Escape preserve panel preference and selection URL',()=>{
 const initial={expanded:false,panelOpen:true};
 const url=modelSelectionUrl('http://localhost/3d?paper=1','m','object');
 const hidden=workspaceLayout(initial,'panel');
 assert.deepEqual(hidden,{expanded:false,panelOpen:false});
 assert.deepEqual(workspaceLayout(workspaceLayout(hidden,'expand'),'escape'),hidden);
 assert.deepEqual(workspaceLayout(workspaceLayout(initial,'expand'),'expand'),initial);
 assert.equal(modelSelectionUrl('http://localhost/3d?paper=1','m','object'),url);
 assert.deepEqual(initial,{expanded:false,panelOpen:true});
});
test('container resize batches renderer updates and cancels on cleanup',()=>{
 const old={ResizeObserver:globalThis.ResizeObserver,requestAnimationFrame:globalThis.requestAnimationFrame,cancelAnimationFrame:globalThis.cancelAnimationFrame};
 let notify, observed,disconnected=false,next=0,resizes=0;const pending=new Map();
 globalThis.ResizeObserver=class{constructor(cb){notify=cb;}observe(el){observed=el;}disconnect(){disconnected=true;}};
 globalThis.requestAnimationFrame=cb=>{pending.set(++next,cb);return next;};
 globalThis.cancelAnimationFrame=id=>pending.delete(id);
 try {
  const container={};const cleanup=observeCanvasResize(container,()=>resizes++);
  assert.equal(observed,container);notify();notify();assert.equal(pending.size,1);
  for(const [id,cb] of pending){pending.delete(id);cb();}
  assert.equal(resizes,1);notify();cleanup();assert.equal(pending.size,0);assert.equal(disconnected,true);
 }finally{Object.assign(globalThis,old);}
});
import {requestLimit} from '../src/lib/request-limit.ts';
test('evidence fan-out is bounded and failed requests release slots',async()=>{
 const limited=requestLimit(2);let active=0,max=0;const releases=[];
 const work=Array.from({length:8},(_,i)=>limited(async()=>{
  active++;max=Math.max(max,active);
  await new Promise(resolve=>releases.push(resolve));active--;
  if(i===2)throw new Error('expected failure');return i;
 }));
 const results=Promise.allSettled(work);
 for(let i=0;i<8;i++){while(!releases.length)await new Promise(resolve=>setImmediate(resolve));releases.shift()();}
 const finished=await results;assert.equal(max,2);assert.equal(active,0);assert.equal(finished.filter(x=>x.status==='fulfilled').length,7);
 assert.equal(await limited(async()=>42),42);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
const require = createRequire(import.meta.url);
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const source = readFileSync(new URL('../src/app/ai-research-preview/page.tsx',import.meta.url),'utf8');
const compiled = ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS}}).outputText;
async function render({enabled=true,generationAvailable,statusError=false,assetError=false,assets=[]}={}) {
  const exports={};
  const dependencies = {
    '@/components/ui/retry-view':{RetryView:()=>React.createElement('button',null,'Retry')},
    '@/lib/evidence-search-state':{parseEvidenceSearch:()=>null},
    '@/components/rag-lite/ask-panel':{AskPanel:props=>React.createElement('section',null,props.generationAvailable?'Evidence form and grounded answers':'Evidence form')},
    '@/lib/api':{getReservoirAssets:async()=>{if(assetError)throw new Error('test unavailable');return assets;}},
    '@/lib/site-scope':{MANAGED_RESERVOIR_ID:'synthetic-reservoir'},
    '@/components/rag-lite/rag-lite.module.css':{default:{}},
  };
  vm.runInNewContext(compiled,{
    exports,require:id=>dependencies[id]??require(id),process:{env:{}},AbortSignal,
    fetch:async(url)=>{
      if(statusError)throw new Error('test network failure');
      const reservoir=new URL(url).searchParams.get('reservoir_id');
      return{ok:true,json:async()=>({enabled,generation_available:reservoir==='synthetic-reservoir'&&generationAvailable})};
    },
  });
  return renderToStaticMarkup(await exports.default({searchParams:Promise.resolve({})}));
}
test('disabled RAG is a feature state, while the core application remains available',async()=>{
  const html=await render({enabled:false});assert.match(html,/search is disabled/);assert.match(html,/core application remains available/);assert.doesNotMatch(html,/Evidence form|Retry/);
});
test('status network failure renders unavailable with retry, not disabled or empty evidence',async()=>{
  const html=await render({statusError:true});assert.match(html,/search is unavailable/);assert.match(html,/Retry/);assert.doesNotMatch(html,/search is disabled|No research assets|Evidence form/);
});
test('asset API failure remains unknown and offers retry instead of a zero count',async()=>{
  const html=await render({assetError:true});assert.match(html,/asset list could not be loaded/);assert.match(html,/not been replaced with zero/);assert.match(html,/Retry/);assert.doesNotMatch(html,/No research assets|Evidence form/);
});
test('a successful empty asset response is distinct from a failed asset API',async()=>{
  const html=await render();assert.match(html,/No research assets are registered/);assert.doesNotMatch(html,/Retry|could not be loaded/);
});
test('only explicit backend readiness for the managed reservoir enables grounded answers',async()=>{
  const assets=[{id:'synthetic-asset',asset_code:'RS-SYNTHETIC',name:'Synthetic asset',parent_asset_id:null}];
  assert.match(await render({assets,generationAvailable:true}),/Evidence form and grounded answers/);
  for(const generationAvailable of [undefined,false,'true']){
    const html=await render({assets,generationAvailable});
    assert.match(html,/Evidence form/);assert.doesNotMatch(html,/grounded answers/);
  }
  assert.doesNotMatch(await render({assets,enabled:false,generationAvailable:true}),/Evidence form/);
});

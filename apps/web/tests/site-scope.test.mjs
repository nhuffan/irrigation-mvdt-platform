import test from 'node:test';
import assert from 'node:assert/strict';
import {MANAGED_RESERVOIR_ID, RESERVOIR_HREF, isManagedReservoir, isResearchAsset, isResearchSource, isResearchModel, visibleDescription} from '../src/lib/site-scope.ts';
test('only the configured reservoir and its research assets enter the workspace',()=>{
 const reservoir_id=MANAGED_RESERVOIR_ID;
 assert.equal(RESERVOIR_HREF,`/reservoirs/${reservoir_id}`);
 assert.equal(isManagedReservoir({id:reservoir_id}),true);
 assert.equal(isManagedReservoir({id:'example-reservoir'}),false);
 assert.equal(isResearchAsset({reservoir_id,asset_code:'RS-ANY'}),true);
 assert.equal(isResearchAsset({reservoir_id,asset_code:'DEV-ANY'}),false);
 assert.equal(isResearchAsset({reservoir_id:'other',asset_code:'RS-ANY'}),false);
 assert.equal(isResearchAsset({reservoir_id,asset_code:'UNCLASSIFIED'}),false);
});
test('documents and models must belong to the managed research scope',()=>{
 const reservoir_id=MANAGED_RESERVOIR_ID;
 assert.equal(isResearchSource({reservoir_id,source_code:'RS-SRC-001'}),true);
 assert.equal(isResearchSource({reservoir_id,source_code:'DEV-DOC'}),false);
 assert.equal(isResearchSource({reservoir_id:'other',source_code:'RS-SRC-001'}),false);
 assert.equal(isResearchModel({reservoir_id,model_code:'RS-MODEL-001'}),true);
 assert.equal(isResearchModel({reservoir_id,model_code:'DEV-MODEL-001'}),false);
 assert.equal(isResearchModel({reservoir_id:'other',model_code:'RS-MODEL-001'}),false);
});
test('demonstration descriptions are omitted while real evidence limitations stay visible',()=>{
 for(const text of ['Development seed record for API integration testing.','Placeholder record for platform testing.','Synthetic example data.',null])assert.equal(visibleDescription(text),null);
 const limitation='Historical source-reported information; current condition not verified.';
 assert.equal(visibleDescription(limitation),limitation);
});

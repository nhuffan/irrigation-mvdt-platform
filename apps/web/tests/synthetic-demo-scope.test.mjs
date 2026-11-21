import assert from 'node:assert/strict';
import test from 'node:test';
import { MANAGED_RESERVOIR_ID, SYNTHETIC_DEMO, isResearchAsset } from '../src/lib/site-scope.ts';
import { GUARDRAIL_QUESTIONS, TRACE_STEP_LABELS } from '../src/lib/rag-lite.ts';

test('research deployment shows only RS- records unless the synthetic demo flag is set', () => {
  assert.equal(SYNTHETIC_DEMO, process.env.NEXT_PUBLIC_SITE_MODE === 'synthetic-demo');
  if (SYNTHETIC_DEMO) return;
  assert.equal(isResearchAsset({ asset_code: 'RS-DT-DAM', reservoir_id: MANAGED_RESERVOIR_ID }), true);
  assert.equal(isResearchAsset({ asset_code: 'DEMO-MAIN-DAM', reservoir_id: MANAGED_RESERVOIR_ID }), false);
});

test('every answer-trace step has a label and guardrail questions stay generic', () => {
  assert.deepEqual(Object.keys(TRACE_STEP_LABELS), ['retrieval', 'authorization', 'model_output', 'citations', 'numbers', 'units', 'content_policy']);
  for (const question of GUARDRAIL_QUESTIONS) assert.doesNotMatch(question, /dau tieng|dầu tiếng/i);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { parseEvidenceSearch, evidenceSearchUrl, evidenceAssetGroups } from '../src/lib/evidence-search-state.ts';
const asset = '11111111-1111-4111-8111-111111111111';
const base = { q: 'cao trình ngưỡng', scope: 'asset', asset, search: 'document', page: '2' };
test('a returned search restores exact scope, query, mode, field and page, never excerpts', () => {
  const state = parseEvidenceSearch(base, [asset]);
  assert.deepEqual(state, { assetId: asset, allDocs: false, question: base.q, queryType: 'document', page: 2 });
  const url = evidenceSearchUrl('/ai-research-preview?other=keep#results', state);
  assert.equal(new URL(url, 'http://local').searchParams.get('q'), base.q);
  assert.match(url, /other=keep/); assert.match(url, /#results$/);
  assert.deepEqual(parseEvidenceSearch(Object.fromEntries(new URL(url, 'http://local').searchParams), [asset]), state);
  const field = parseEvidenceSearch({ ...base, search: 'attribute', field: 'reported_sill_elevation' }, [asset]);
  assert.equal(field.attributeKey, 'reported_sill_elevation');
  const corpus = parseEvidenceSearch({ ...base, asset: '', scope: 'corpus' }, []);
  assert.equal(corpus.assetId, ''); assert.equal(corpus.allDocs, true);
  assert.equal(evidenceSearchUrl(url, null), '/ai-research-preview?other=keep#results');
});
test('stale or malformed return queries cannot select unknown assets or broaden the scope', () => {
  for (const patch of [
    { asset: 'unknown' }, { asset: '' }, { scope: '' }, { scope: 'all' },
    { scope: 'corpus' }, { scope: 'corpus', asset: '', search: 'auto' },
    { scope: 'corpus', asset: '', field: 'reported_sill_elevation' },
    { search: 'generated' }, { field: 'reported_discharge' },
    { search: 'attribute', field: '../other' },
    { q: 'x' }, { q: 'x'.repeat(1001) }, { q: ['one', 'two'] },
    { page: '0' }, { page: '-1' }, { page: '1.5' }, { page: '10001' }, { page: ['1', '2'] },
  ]) assert.equal(parseEvidenceSearch({ ...base, ...patch }, [asset]), null, JSON.stringify(patch));
});
test('grouped selection preserves all exact asset UUIDs including parents without inherited scope', () => {
  const assets = [{ id: 'dam', parent_asset_id: null }, { id: 'intake', parent_asset_id: null },
    { id: 'c1', parent_asset_id: 'intake' }, { id: 'c2', parent_asset_id: 'intake' },
    { id: 'deep', parent_asset_id: 'c1' }, { id: 'orphan', parent_asset_id: 'missing' }];
  const groups = evidenceAssetGroups(assets);
  assert.deepEqual(groups.find(g => g.parent.id === 'intake').children.map(a => a.id), ['c1', 'c2']);
  assert.deepEqual(groups.flatMap(g => [g.parent.id, ...g.children.map(a => a.id)]).sort(), assets.map(a => a.id).sort());
  assert.equal(groups.find(g => g.parent.id === 'intake').parent, assets[1]);
});

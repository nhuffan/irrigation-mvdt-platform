import test from 'node:test';
import assert from 'node:assert/strict';
import { publicDataSource, publicAssets, publicExplorerRecords, publicModels } from '../src/lib/public-client-data.ts';

const actor = 'Private Reviewer Example';
const receipt = '/Users/private/review/receipt.json';
const source = () => ({
  id: 'source', reservoir_id: 'reservoir', source_code: 'RS-SRC-001', source_type: 'TECHNICAL_REPORT',
  title: 'Source title', file_name: 'report.pdf', source_date: '2020-01-02', source_owner: actor,
  authority_level: 'UNKNOWN', verification_status: 'UNVERIFIED', notes: `Receipt ${receipt}`,
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-02T00:00:00Z',
  reviewer_receipt: receipt, signature: actor,
});
const asset = () => ({
  id: 'asset', reservoir_id: 'reservoir', parent_asset_id: null, asset_code: 'RS-ASSET',
  name: 'Canonical asset name', description: `Evidence ${receipt}`, technical_description: null,
  condition_status: null, data_status: 'REGISTERED', category: { id: 'category', code: 'RS-CAT', name: 'Category', private_path: receipt },
  geometry: null, location: {
    location_status: 'REFERENCE_LOCATION', geometry: { type: 'Point', coordinates: [106.3, 11.3], receipt },
    geometry_type: 'Point', crs: 'EPSG:4326', source: 'Public map', source_url: 'https://example.org/map.pdf',
    locator: 'PDF:p22:Table2.1', evidence_id: 'evidence', accuracy_limitation: 'Reference only',
    verification_note: 'No surveyed geometry', reviewer: actor, reviewed_at: '2026-01-02T00:00:00Z', review_state: 'AVAILABLE',
    reviewer_receipt: receipt,
  }, reviewer_receipt: receipt,
});
const technical = () => ({
  id: 'field', asset_id: 'asset', source_id: 'source', source: source(), verification_status: 'VERIFIED',
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-02T00:00:00Z',
  attribute_key: 'historic_discharge', attribute_label: 'Discharge — Lưu lượng', value_number: 0, value_text: null, unit: 'm3/s',
  reviewed_provenance: {
    verification_level: 'L2', source_code: 'RS-SRC-001', evidence_id: 'evidence',
    source_locator: 'PDF:p47:Table2.2; existing condition; +13 m', authority: 'SOURCE_REPORTED',
    reviewer: actor, reviewed_at: '2026-01-02T00:00:00Z', receipt,
  }, private_path: receipt,
});
const condition = () => ({
  id: 'condition', asset_id: 'asset', source_id: 'source', source: source(), verification_status: 'VERIFIED',
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-02T00:00:00Z',
  condition_date: '2020-01-01', condition_status: 'HISTORICAL', summary: null,
  defect_description: null, recommended_action: null, reviewer_receipt: receipt,
});
const records = () => ({ asset: {
  technical: [technical()], condition: condition(), conditionError: false,
  events: [{ record_id: 'event', asset_id: 'asset', source_id: 'source', source: source(), event_type: 'INSPECTION', event_date: '2020-01-01', title: 'Historic record', summary: null, verification_status: 'VERIFIED', inspector: actor }],
  documents: [{ id: 'document', source_id: 'source', document_code: 'DOC', original_file_name: 'report.pdf', mime_type: 'application/pdf', file_size: 0, checksum_sha256: 'a'.repeat(64), page_count: 0, uploaded_at: '2026-01-01T00:00:00Z', source: source(), storage_key: receipt }],
  links: [{ id: 'link', model_id: 'model', asset_id: 'asset', reservoir_id: 'reservoir', object_key: 'G-No_Name_008', object_name: 'Main roof', verification_status: 'VERIFIED', reviewer_receipt: receipt }],
  reviewer_receipt: receipt,
} });
const model = () => ({
  id: 'model', reservoir_id: 'reservoir', source_id: 'source', source: source(), model_code: 'RS-MODEL',
  name: 'Representative LOCAL model', model_type: 'SKETCH', format: 'glb', coordinate_mode: 'LOCAL',
  longitude: null, latitude: null, height: null, heading: 0, pitch: 0, roll: 0, scale: 1,
  verification_status: 'VERIFIED', storage_key: receipt,
});
function noPrivate(value) {
  const json = JSON.stringify(value);
  for (const forbidden of [actor, receipt, '/Users/', 'reviewer_receipt', 'signature', 'storage_key', 'private_path']) {
    assert.ok(!json.includes(forbidden), forbidden);
  }
}

test('source client allowlist preserves provenance identities and suppresses owner/freeform receipt data', () => {
  const raw = source();
  const before = structuredClone(raw);
  const shown = publicDataSource(raw);
  assert.equal(shown.source_owner, null);
  assert.equal(shown.notes, null);
  for (const key of ['id', 'reservoir_id', 'source_code', 'title', 'file_name', 'source_date', 'authority_level', 'verification_status', 'created_at', 'updated_at']) {
    assert.equal(shown[key], raw[key], key);
  }
  noPrivate(shown);
  assert.deepEqual(raw, before, 'raw API source must not be mutated');
  assert.equal(publicDataSource(null), null);
});

test('asset client allowlist removes location reviewer/receipt and retains exact reference geometry and hierarchy', () => {
  const raw = asset();
  const before = structuredClone(raw);
  const [shown] = publicAssets([raw]);
  assert.equal(shown.location.reviewer, null);
  for (const key of ['id', 'asset_code', 'parent_asset_id', 'name', 'data_status']) assert.equal(shown[key], raw[key]);
  assert.equal(shown.geometry, null);
  assert.deepEqual(shown.location.geometry, { type: 'Point', coordinates: [106.3, 11.3] });
  assert.equal(shown.location.locator, raw.location.locator);
  assert.equal(shown.location.reviewed_at, raw.location.reviewed_at);
  noPrivate(shown);
  assert.deepEqual(raw, before);
  assert.equal(publicAssets([{ ...raw, location: null }])[0].location, null);
  assert.equal(publicAssets([{ ...raw, geometry: undefined, location: undefined }])[0].geometry, undefined);
});

test('every nested client source and record is projected without changing technical values/units/locators or counts', () => {
  const raw = records();
  const before = structuredClone(raw);
  const shown = publicExplorerRecords(raw);
  noPrivate(shown);
  for (const key of ['technical', 'events', 'documents', 'links']) assert.equal(shown.asset[key].length, raw.asset[key].length);
  const field = shown.asset.technical[0];
  for (const key of ['id', 'asset_id', 'source_id', 'attribute_key', 'attribute_label', 'value_number', 'value_text', 'unit', 'verification_status']) assert.equal(field[key], raw.asset.technical[0][key], key);
  assert.equal(field.value_number, 0);
  assert.equal(field.reviewed_provenance.reviewer, 'Not published');
  assert.equal(field.reviewed_provenance.source_locator, raw.asset.technical[0].reviewed_provenance.source_locator);
  assert.equal(field.reviewed_provenance.reviewed_at, raw.asset.technical[0].reviewed_provenance.reviewed_at);
  assert.equal(shown.asset.documents[0].file_size, 0);
  assert.equal(shown.asset.documents[0].page_count, 0);
  assert.equal(shown.asset.links[0].object_key, raw.asset.links[0].object_key);
  assert.deepEqual(raw, before, 'canonical server-side records/readback must remain untouched');
});

test('client projection preserves unavailable/empty distinctions instead of manufacturing records', () => {
  const empty = { technical: [], events: [], documents: [], links: [], condition: null, conditionError: false };
  const unavailable = { technical: null, events: null, documents: null, links: null, condition: null, conditionError: true };
  assert.deepEqual(publicExplorerRecords({ empty, unavailable }), { empty, unavailable });
  const noProvenance = records();
  noProvenance.asset.technical[0].reviewed_provenance = null;
  assert.equal(publicExplorerRecords(noProvenance).asset.technical[0].reviewed_provenance, null);
});

test('3D client projection removes source owner/receipts and preserves LOCAL mode, camera placement and stable IDs', () => {
  const raw = model();
  const before = structuredClone(raw);
  const [shown] = publicModels([raw]);
  noPrivate(shown);
  for (const key of ['id', 'source_id', 'model_code', 'name', 'coordinate_mode', 'longitude', 'latitude', 'height', 'heading', 'pitch', 'roll', 'scale', 'verification_status']) assert.equal(shown[key], raw[key], key);
  assert.deepEqual(raw, before);
  assert.equal(publicModels([{ ...raw, source: null }])[0].source, null);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { citationHref, displayValue, groupDocuments, needsOpenLimitations, resultHeading } from '../src/lib/rag-lite.ts';

const ASSET = '11111111-1111-4111-8111-111111111111';
const OTHER = '22222222-2222-4222-8222-222222222222';
const SOURCE = '33333333-3333-4333-8333-333333333333';
const DOCUMENT = '44444444-4444-4444-8444-444444444444';
const RECORD = '55555555-5555-4555-8555-555555555555';
const attribute = (patch = {}) => ({
  citation_id: 'attr-record-fingerprint', kind: 'technical_attribute',
  source_id: SOURCE, source_code: 'Source 1', document_id: null, record_id: RECORD,
  page: null, locator: 'Table 2, main cylinder', asset_id: ASSET, url: `/assets/${ASSET}`,
  content_url: null, title: 'Design pressure', excerpt: 'Design pressure: 0 MPa',
  checksum_sha256: null, attribute_key: 'design_pressure', value_number: 0,
  value_text: null, unit: 'MPa', evidence_id: 'EVID-01', source_date: null,
  record_status: 'UNVERIFIED', source_status: 'UNVERIFIED', authority: null, ...patch,
});
const document = (patch = {}) => ({
  ...attribute(), citation_id: 'doc-original-chunk-id', kind: 'document_chunk',
  document_id: DOCUMENT, record_id: null, page: 10, locator: 'PDF:p10',
  url: `/documents/${DOCUMENT}`, content_url: `/api/media/documents/${DOCUMENT}#page=10`,
  title: 'Original technical report.pdf', excerpt: 'Original excerpt, unchanged.',
  checksum_sha256: 'a'.repeat(64), attribute_key: null, value_number: null,
  unit: null, evidence_id: null, record_status: null, ...patch,
});
const result = (patch = {}) => ({
  status: 'RETRIEVAL_ONLY', answer: null, asset_id: ASSET,
  citations: [attribute()], limitations: [], ...patch,
});

test('retrieval and generation outcomes remain distinct while retained evidence stays available', () => {
  const scenarios = [
    ['RETRIEVAL_ONLY', 'Supporting evidence found'],
    ['NOT_ENOUGH_EVIDENCE', 'No supporting evidence found'],
    ['GENERATION_UNAVAILABLE', 'Evidence found · AI summary unavailable'],
    ['ANSWERED', 'Evidence-backed answer'],
  ];
  for (const [status, expected] of scenarios) assert.equal(resultHeading(result({ status })), expected);
  assert.equal(resultHeading(result({ status: 'GENERATION_UNAVAILABLE', citations: [] })), 'No supporting evidence found');
});

test('exact source values retain numeric zero, original spelling and empty text without translation', () => {
  assert.equal(displayValue(attribute()), '0 MPa');
  assert.equal(displayValue(attribute({ value_number: 15.75, unit: 'm3/s' })), '15.75 m3/s');
  assert.equal(displayValue(attribute({ value_number: null, value_text: 'Kênh Đông', unit: 'text' })), 'Kênh Đông');
  assert.equal(displayValue(attribute({ value_number: null, value_text: '0', unit: 'text' })), '0');
  assert.equal(displayValue(attribute({ value_number: null, value_text: '', unit: 'text' })), '');
  assert.equal(displayValue(attribute({ value_number: null, value_text: '  ', unit: null })), '  ');
  assert.equal(displayValue(attribute({ value_number: null, value_text: null })), 'Unknown');
  assert.equal(displayValue(attribute({ value_number: 0, value_text: 'source note', unit: 'count' })), '0 count');
});

test('invalid numeric values cannot be presented as measured numbers', () => {
  for (const value_number of [Infinity, -Infinity, NaN]) {
    assert.equal(displayValue(attribute({ value_number })), 'Unknown');
    assert.equal(displayValue(attribute({ value_number, value_text: 'Original text', unit: 'text' })), 'Original text');
  }
});

test('document grouping preserves all ranked passages, original objects and first-document order', () => {
  const a = document({ citation_id: 'first', excerpt: 'First ranked passage' });
  const b = document({ citation_id: 'second', document_id: OTHER });
  const c = document({ citation_id: 'third', excerpt: 'Lower ranked passage' });
  const attr = attribute();
  const missing = document({ citation_id: 'missing-id', document_id: null });
  const input = Object.freeze([a, b, attr, c, missing]);
  const groups = groupDocuments(input);
  assert.deepEqual(groups.map(group => group.documentId), [DOCUMENT, OTHER, 'unresolved:missing-id']);
  assert.deepEqual(groups.flatMap(group => group.citations).map(entry => entry.citation_id), ['first', 'third', 'second', 'missing-id']);
  assert.equal(groups[0].citations[0], a);
  assert.equal(groups[0].citations[1], c);
  assert.equal(groups.reduce((count, group) => count + group.citations.length, 0), 4);
  assert.deepEqual(input, [a, b, attr, c, missing]);
  assert.deepEqual(groupDocuments([attr]), []);
});

test('technical evidence and source actions retain the exact asset rather than its parent or another asset', () => {
  assert.equal(citationHref(attribute(), 'evidence'), `/assets/${ASSET}#record-${RECORD}`);
  assert.equal(citationHref(attribute(), 'source'), `/data-sources/${SOURCE}/documents`);
  assert.equal(citationHref(attribute(), 'original'), null);
  assert.equal(citationHref(attribute(), 'download'), null);
  for (const patch of [
    { url: `/assets/${OTHER}` }, { asset_id: null }, { record_id: null },
    { record_id: '../outside' }, { record_id: `${RECORD}#other` },
    { url: `/assets/${ASSET}#record-${RECORD}` },
    { asset_id: '../outside' }, { document_id: DOCUMENT },
  ]) for (const kind of ['evidence', 'source', 'original', 'download']) {
    assert.equal(citationHref(attribute(patch), kind), null, JSON.stringify({ patch, kind }));
  }
});

test('PDF actions use the physical page and the document ID, including corpus-wide passages', () => {
  for (const asset_id of [ASSET, null]) {
    const citation = document({ asset_id });
    assert.equal(citationHref(citation, 'evidence'), `/documents/${DOCUMENT}`);
    assert.equal(citationHref(citation, 'source'), `/data-sources/${SOURCE}/documents`);
    assert.equal(citationHref(citation, 'original'), `/api/media/documents/${DOCUMENT}#page=10`);
    assert.equal(citationHref(citation, 'download'), `/api/media/documents/${DOCUMENT}?download=true`);
  }
});

test('missing page/content metadata falls back to the safe document action without inventing a page', () => {
  for (const patch of [{ page: null }, { page: 0 }, { page: -1 }, { page: 1.5 }, { page: NaN }, { page: Infinity }, { page: '10' }, { content_url: null }]) {
    const citation = document(patch);
    assert.equal(citationHref(citation, 'evidence'), `/documents/${DOCUMENT}`);
    assert.equal(citationHref(citation, 'original'), null);
    assert.equal(citationHref(citation, 'download'), null);
  }
});

test('external, encoded or mismatched evidence routes never become links', () => {
  const urls = [
    `https://other.invalid/documents/${DOCUMENT}`, `//other.invalid/documents/${DOCUMENT}`,
    'javascript:alert(1)', ` /documents/${DOCUMENT}`, `/documents/${OTHER}`,
    `/documents/${DOCUMENT}?redirect=https://other.invalid`, `/documents/${DOCUMENT}#page=10`,
    `/documents/%34${DOCUMENT.slice(1)}`, `/documents/${DOCUMENT}/../${OTHER}`,
    `/\\other.invalid/documents/${DOCUMENT}`,
  ];
  for (const url of urls) for (const kind of ['evidence', 'source', 'original', 'download']) {
    assert.equal(citationHref(document({ url }), kind), null, `${kind}: ${url}`);
  }
});

test('original PDF links reject another document, wrong physical page, redirects and external content', () => {
  for (const content_url of [
    `/api/media/documents/${OTHER}#page=10`, `/api/media/documents/${DOCUMENT}#page=9`,
    `/api/media/documents/${DOCUMENT}#page=010`, `/api/media/documents/${DOCUMENT}?download=true#page=10`,
    `https://other.invalid/api/media/documents/${DOCUMENT}#page=10`,
    `//other.invalid/api/media/documents/${DOCUMENT}#page=10`,
    `/api/media/documents/${DOCUMENT}%23page=10`, 'javascript:alert(1)',
  ]) for (const kind of ['original', 'download']) {
    assert.equal(citationHref(document({ content_url }), kind), null, `${kind}: ${content_url}`);
  }
});

test('UUID checks reject traversal and malformed metadata before constructing any route', () => {
  for (const bad of ['', '../outside', 'a'.repeat(36), `${DOCUMENT}/child`, `${DOCUMENT}?x=1`, DOCUMENT.replaceAll('-', '')]) {
    for (const field of ['source_id', 'document_id', 'asset_id']) {
      const citation = document({ [field]: bad });
      for (const kind of ['evidence', 'source', 'original', 'download']) assert.equal(citationHref(citation, kind), null, `${field}: ${bad}`);
    }
  }
});

test('no evidence and actionable integrity problems open full limitations automatically', () => {
  assert.equal(needsOpenLimitations(result({ citations: [] })), true);
  assert.equal(needsOpenLimitations(result({ status: 'NOT_ENOUGH_EVIDENCE' })), true);
  for (const line of [
    'An authorized document is missing, stale or invalid; rebuild its local index',
    'PDF checksum mismatch detected', 'Document integrity validation failed',
    'The requested PDF is not authorized', 'Unauthorized source document', 'Authorization revoked',
  ]) assert.equal(needsOpenLimitations(result({ limitations: [line] })), true, line);
});

test('standard research caveats and unavailable generation do not overwhelm successful retrieval', () => {
  const limitations = [
    'Experimental future work — human verification required',
    'HISTORICAL / REFERENCE evidence; no current condition, operating decision or domain validation',
    'Keyword retrieval; extraction may damage tables. Check the original PDF and locator',
    'A reviewed attribute does not promote its source authority; unknown source dates remain unknown',
    'An authorized PDF has no usable extracted text; OCR is outside scope',
    'Corpus-wide passages are not attributed to any particular asset',
    'Generation unavailable or invalid; original retrieval evidence retained',
  ];
  assert.equal(needsOpenLimitations(result({ status: 'GENERATION_UNAVAILABLE', limitations })), false);
});


test('empty results distinguish unavailable or stale evidence from a completed search with no match', () => {
  for (const limitation of [
    'An authorized document is missing, stale or invalid; rebuild its local index',
    'PDF checksum mismatch detected',
    'Document integrity validation failed',
    'Authorization revoked',
  ]) {
    const unavailable = result({ status: 'NOT_ENOUGH_EVIDENCE', citations: [], limitations: [limitation] });
    assert.equal(resultHeading(unavailable), 'Evidence retrieval unavailable', limitation);
    assert.equal(needsOpenLimitations(unavailable), true, limitation);
  }
  const noMatch = result({
    status: 'NOT_ENOUGH_EVIDENCE', citations: [],
    limitations: ['No matching reviewed direct attribute; no parent/child inheritance'],
  });
  assert.equal(resultHeading(noMatch), 'No supporting evidence found');
});

test('partial retrieval keeps every valid passage while clearly disclosing an incomplete search', () => {
  const citations = [document({ citation_id: 'page-10' }), document({ citation_id: 'page-9', page: 9 })];
  const partial = result({ citations, limitations: ['An authorized document is missing, stale or invalid; rebuild its local index'] });
  assert.equal(resultHeading(partial), 'Supporting evidence found · search incomplete');
  assert.equal(needsOpenLimitations(partial), true);
  assert.deepEqual(groupDocuments(partial.citations)[0].citations, citations);
  assert.equal(resultHeading({ ...partial, status: 'ANSWERED', answer: 'Source-backed text' }), 'Evidence-backed answer');
});

test('provider failure and limited text coverage are distinct from document integrity failure', () => {
  const limitations = [
    'Generation unavailable or invalid; original retrieval evidence retained',
    'An authorized PDF has no usable extracted text; OCR is outside scope',
    'Keyword retrieval; extraction may damage tables. Check the original PDF and locator',
  ];
  const retained = result({ status: 'GENERATION_UNAVAILABLE', limitations });
  assert.equal(resultHeading(retained), 'Evidence found · AI summary unavailable');
  assert.equal(needsOpenLimitations(retained), false);
  assert.equal(resultHeading({ ...retained, citations: [] }), 'No supporting evidence found');
});

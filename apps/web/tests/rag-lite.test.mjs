import test from 'node:test';
import assert from 'node:assert/strict';
import { citationHref, displayValue, evidenceReasonText, metadataLabel, groupDocuments, criticalRetrievalIssue, searchFeedback, paginationItems } from '../src/lib/rag-lite.ts';

const resultHeading = result => searchFeedback(result).title;

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
    ['RETRIEVAL_ONLY', '1 reference'],
    ['GENERATION_UNAVAILABLE', '1 reference'],
    ['ANSWERED', '1 reference'],
  ];
  for (const [status, expected] of scenarios) assert.equal(resultHeading(result({ status })), expected);
  assert.equal(resultHeading(result({ status: 'GENERATION_UNAVAILABLE', citations: [] })), 'No matches');
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

test('only integrity failures are treated as incomplete searches', () => {
  assert.equal(criticalRetrievalIssue(result({ citations: [] })), false);
  assert.equal(criticalRetrievalIssue(result({ status: 'NOT_ENOUGH_EVIDENCE' })), false);
  for (const line of [
    'An authorized document is missing, stale or invalid; rebuild its local index',
    'PDF checksum mismatch detected', 'Document integrity validation failed',
    'The requested PDF is not authorized', 'Unauthorized source document', 'Authorization revoked',
  ]) assert.equal(criticalRetrievalIssue(result({ limitations: [line] })), true, line);
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
  assert.equal(criticalRetrievalIssue(result({ status: 'GENERATION_UNAVAILABLE', limitations })), false);
});


test('empty results distinguish unavailable or stale evidence from a completed search with no match', () => {
  for (const limitation of [
    'An authorized document is missing, stale or invalid; rebuild its local index',
    'PDF checksum mismatch detected',
    'Document integrity validation failed',
    'Authorization revoked',
  ]) {
    const unavailable = result({ status: 'NOT_ENOUGH_EVIDENCE', citations: [], limitations: [limitation] });
    assert.equal(resultHeading(unavailable), 'Documents unavailable', limitation);
    assert.equal(criticalRetrievalIssue(unavailable), true, limitation);
  }
  const noMatch = result({
    status: 'NOT_ENOUGH_EVIDENCE', citations: [],
    limitations: ['No matching reviewed direct attribute; no parent/child inheritance'],
  });
  assert.equal(resultHeading(noMatch), 'No matches');
});

test('partial retrieval keeps every valid passage while clearly disclosing an incomplete search', () => {
  const citations = [document({ citation_id: 'page-10' }), document({ citation_id: 'page-9', page: 9 })];
  const partial = result({ citations, limitations: ['An authorized document is missing, stale or invalid; rebuild its local index'] });
  assert.equal(resultHeading(partial), '2 references · incomplete');
  assert.equal(criticalRetrievalIssue(partial), true);
  assert.deepEqual(groupDocuments(partial.citations)[0].citations, citations);
  assert.equal(resultHeading({ ...partial, status: 'ANSWERED', answer: 'Source-backed text' }), '2 references · incomplete');
});

test('provider failure and limited text coverage are distinct from document integrity failure', () => {
  const limitations = [
    'Generation unavailable or invalid; original retrieval evidence retained',
    'An authorized PDF has no usable extracted text; OCR is outside scope',
    'Keyword retrieval; extraction may damage tables. Check the original PDF and locator',
  ];
  const retained = result({ status: 'GENERATION_UNAVAILABLE', limitations });
  assert.equal(resultHeading(retained), '1 reference');
  assert.equal(criticalRetrievalIssue(retained), false);
  assert.equal(resultHeading({ ...retained, citations: [] }), 'No matches');
});


test('structured empty reasons distinguish absent links, limited text, authorization and completed no-match', () => {
  const codes = ['NO_DIRECT_DOCUMENT', 'NO_REVIEWED_ATTRIBUTE', 'NOT_AUTHORIZED', 'IMAGE_ONLY', 'INDEX_INVALID', 'DOCUMENT_MISSING', 'DOCUMENT_INVALID', 'EXTRACTION_LIMITED', 'NO_MATCH', 'SOURCE_METADATA_UNKNOWN', 'OUT_OF_SCOPE', 'SCOPE_MISMATCH'];
  const messages = codes.map(evidenceReasonText);
  assert.equal(new Set(messages).size, codes.length);
  assert.ok(messages.every(message => typeof message === 'string' && message.length > 0));
  assert.match(evidenceReasonText('NO_DIRECT_DOCUMENT'), /Technical records may still be available/);
  assert.match(evidenceReasonText('IMAGE_ONLY'), /no OCR/);
  assert.match(evidenceReasonText('SOURCE_METADATA_UNKNOWN'), /not independent/);
  assert.equal(evidenceReasonText('unknown-future-code'), null);
});

test('structured integrity errors retain all valid citations and differ from authorization or text coverage', () => {
  for (const code of ['INDEX_INVALID', 'DOCUMENT_MISSING', 'DOCUMENT_INVALID']) {
    assert.equal(resultHeading(result({ reason_codes: [code] })), '1 reference · incomplete');
    assert.equal(resultHeading(result({ citations: [], reason_codes: [code], status: 'NOT_ENOUGH_EVIDENCE' })), 'Documents unavailable');
  }
  for (const [code, title] of [['NO_DIRECT_DOCUMENT', 'No matching evidence'], ['NOT_AUTHORIZED', 'Search access limited'], ['IMAGE_ONLY', 'No searchable text'], ['EXTRACTION_LIMITED', 'No searchable match'], ['NO_MATCH', 'No matches'], ['SOURCE_METADATA_UNKNOWN', 'No matches']]) {
    assert.equal(resultHeading(result({ citations: [], reason_codes: [code], status: 'NOT_ENOUGH_EVIDENCE' })), title);
  }
});

test('absent source metadata is visibly Unknown without inventing a source date or authority', () => {
  for (const value of [null, undefined, '', ' ', 'UNKNOWN']) assert.equal(metadataLabel(value), 'Unknown');
  assert.equal(metadataLabel('UNVERIFIED'), 'UNVERIFIED');
  assert.equal(metadataLabel('2026-01-01'), '2026-01-01');
});


test('one short outcome prioritizes scope and unavailable evidence over generic empty guidance', () => {
  const empty = codes => result({ status: 'NOT_ENOUGH_EVIDENCE', citations: [], reason_codes: codes });
  assert.equal(searchFeedback(empty(['NO_DIRECT_DOCUMENT', 'NO_REVIEWED_ATTRIBUTE'])).title, 'No linked evidence');
  assert.equal(searchFeedback(empty(['OUT_OF_SCOPE', 'NO_DIRECT_DOCUMENT'])).title, 'Outside search scope');
  assert.equal(searchFeedback(empty(['SCOPE_MISMATCH'])).title, 'Check the selected asset');
  assert.equal(searchFeedback(empty(['IMAGE_ONLY', 'NO_MATCH'])).title, 'No matches');
  assert.equal(searchFeedback(result()).description, '');
  assert.match(searchFeedback(result({ status: 'GENERATION_UNAVAILABLE' })).description, /original evidence/);
});


test('pagination shows every page for small result sets and bounds long page controls', () => {
  assert.deepEqual(paginationItems(1, 0), []);
  for (const page of [1, 2, 3]) assert.deepEqual(paginationItems(page, 3), [1, 2, 3]);
  assert.deepEqual(paginationItems(1, 6), [1, 2, 3, 4, 5, 6]);
  assert.deepEqual(paginationItems(1, 20), [1, 2, 3, 4, 5, "…", 20]);
  assert.deepEqual(paginationItems(10, 20), [1, "…", 9, 10, 11, "…", 20]);
  assert.deepEqual(paginationItems(20, 20), [1, "…", 16, 17, 18, 19, 20]);
});

test('result heading uses the full count, while current-page grouping retains every returned citation', () => {
  const current = [document({citation_id:'page6'}), document({citation_id:'page7', page:9})];
  const paged = result({ citations: current, pagination: {page:2, page_size:5, total_results:12, total_pages:3} });
  assert.equal(searchFeedback(paged).title, '12 references');
  assert.deepEqual(groupDocuments(paged.citations)[0].citations, current);
  assert.equal(searchFeedback({...paged, reason_codes:['INDEX_INVALID']}).title, '12 references · incomplete');
});

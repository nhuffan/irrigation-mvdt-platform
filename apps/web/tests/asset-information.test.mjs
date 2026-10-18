import test from 'node:test';
import assert from 'node:assert/strict';
import { technicalValueDetails, linkedDocumentCounts, publicEvidenceText, publicEvidenceHref } from '../src/lib/asset-information.ts';
import { technicalCoverage } from '../src/lib/asset-coverage.ts';
import { descendantIds, l2Count, hierarchyCoverage } from '../src/lib/asset-hierarchy.ts';

const record = (value_number = null, value_text = null, unit = null) => ({ value_number, value_text, unit });

test('numeric zero survives null/blank text and units retain their exact reported spelling', () => {
  for (const text of [null, '', '   ']) {
    const value = technicalValueDetails(record(0, text, 'm3/s'));
    assert.equal(value.value, 0);
    assert.equal(value.valueState, 'AVAILABLE');
    assert.equal(value.unit, 'm3/s');
    assert.equal(value.valueUnit, 'm3/s');
  }
  assert.equal(technicalValueDetails(record(15.75, null, 'm')).value, 15.75);
});

test('null and empty text retain different missingness states without inventing zero', () => {
  const missing = technicalValueDetails(record());
  assert.equal(missing.valueState, 'MISSING');
  assert.equal(missing.value, 'Not available');
  for (const text of ['', '  ']) {
    const empty = technicalValueDetails(record(null, text));
    assert.equal(empty.valueState, 'EMPTY_TEXT');
    assert.equal(empty.value, 'Empty text in source record');
  }
  assert.equal(technicalValueDetails(record(Number.NaN)).valueState, 'INVALID_NUMBER');
  assert.equal(technicalValueDetails(record(Infinity)).valueState, 'INVALID_NUMBER');
  assert.equal(missing.unit, 'Not reported');
  assert.equal(technicalValueDetails(record(null, null, '')).unit, 'Not reported (empty unit)');
});

test('text semantics remain explicit without appending literal text as a physical unit', () => {
  const value = technicalValueDetails(record(null, 'Kênh Đông', 'text'));
  assert.equal(value.value, 'East Canal — Kênh Đông');
  assert.equal(value.unit, 'Text value (no physical unit)');
  assert.equal(value.valueUnit, null);
  assert.equal(value.valueState, 'AVAILABLE');
  assert.equal(technicalValueDetails(record(null, '0', 'text')).value, '0');
});

test('number and source text coexist without silently dropping either value', () => {
  const value = technicalValueDetails(record(0, 'At design condition', 'count'));
  assert.equal(value.value, 0);
  assert.equal(value.additionalText, 'At design condition');
  assert.equal(value.valueUnit, 'count');
});

test('document edges and distinct linked PDF hashes use different denominators', () => {
  const hash = 'a'.repeat(64);
  const other = 'b'.repeat(64);
  const documents = [
    { id: 'edge1', mime_type: 'application/pdf', checksum_sha256: hash },
    { id: 'edge2', mime_type: 'application/pdf', checksum_sha256: hash.toUpperCase() },
    { id: 'edge3', mime_type: 'application/pdf; charset=binary', checksum_sha256: other },
    { id: 'image', mime_type: 'image/png', checksum_sha256: 'c'.repeat(64) },
  ];
  assert.deepEqual(linkedDocumentCounts(documents), { edges: 4, distinctPdfHashes: 2, unhashablePdfs: 0 });
  assert.deepEqual(linkedDocumentCounts([]), { edges: 0, distinctPdfHashes: 0, unhashablePdfs: 0 });
  assert.deepEqual(linkedDocumentCounts([{ id: 'unknown-type', mime_type: null, checksum_sha256: hash }]), { edges: 1, distinctPdfHashes: null, unhashablePdfs: 0 });
  assert.deepEqual(linkedDocumentCounts(null), { edges: null, distinctPdfHashes: null, unhashablePdfs: null });
  assert.deepEqual(linkedDocumentCounts([{ id: 'unknown', mime_type: 'application/pdf', checksum_sha256: null }]), { edges: 1, distinctPdfHashes: null, unhashablePdfs: 1 });
});

test('parent direct zero stays separate from descendant L2 and failed reads remain unknown', () => {
  const assets = [
    { id: 'parent', parent_asset_id: null },
    { id: 'child1', parent_asset_id: 'parent' },
    { id: 'child2', parent_asset_id: 'parent' },
  ];
  const l2 = { reviewed_provenance: { verification_level: 'L2' } };
  const records = { parent: [], child1: [l2, l2], child2: [l2] };
  assert.equal(l2Count(['parent'], records), 0);
  assert.equal(technicalCoverage({ technical: [] }), '0 direct records');
  assert.equal(technicalCoverage({ technical: null }), 'Unavailable');
  assert.equal(l2Count(descendantIds(assets, 'parent'), records), 3);
  assert.deepEqual(hierarchyCoverage(assets, records), { primary: 0, components: 3, all: 3 });
  assert.equal(l2Count(descendantIds(assets, 'parent'), { ...records, child2: null }), null);
  assert.equal(l2Count([], records), 0);
});

test('publication display removes private paths while preserving exact ordinary locators', () => {
  const locator = 'PDF:p47:printed47:index46:culvert1:reported_discharge; Table 2.2; existing condition';
  assert.equal(publicEvidenceText(locator), locator);
  for (const path of ['/Users/reviewer/private/source.pdf', '/home/reviewer/source.pdf', 'file:///Users/reviewer/source.pdf', 'C:\\Users\\reviewer\\source.pdf', '/private/tmp/file.pdf']) {
    const shown = publicEvidenceText(`Evidence ${path} pending`);
    assert.ok(!shown.includes(path));
    assert.ok(!shown.includes('reviewer'));
    assert.match(shown, /private path omitted/);
  }
  assert.equal(publicEvidenceText(null), 'Not available');
});

test('source links allow public HTTP(S) or own paths without credentials or private targets', () => {
  for (const href of ['https://documents.worldbank.org/report.pdf#page=22', 'http://example.org/source.pdf', '/documents/a#page=3', '/methodology#coverage']) {
    assert.equal(publicEvidenceHref(href), href);
  }
  for (const href of ['javascript:alert(1)', '//other.invalid/source.pdf', 'file:///Users/reviewer/source.pdf', '/Users/reviewer/source.pdf', 'https://user:password@example.org/source.pdf', 'https://example.org/%2FUsers/reviewer/source.pdf', 'https://localhost/source.pdf', 'http://127.0.0.1/file', 'http://192.168.1.1/file', 'http://172.16.0.1/file', 'http://10.0.0.1/file', 'http://[::1]/file', 'https://example.org/file?token=private', '/documents/a?key=private', '/\\other.invalid/file', ' https://example.org/file']) {
    assert.equal(publicEvidenceHref(href), null, href);
  }
});

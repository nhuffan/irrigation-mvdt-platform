import test from 'node:test';
import assert from 'node:assert/strict';
import { originalDocumentUrl, documentMediaError } from '../src/lib/document-preview.ts';
import { documentPage, documentHref } from '../src/lib/document-navigation.ts';
const id = '224161a4-a365-51fa-8885-6b7be6d6a433';
test('original physical page survives a detail roundtrip without renumbering partial extraction', () => {
  const source = `/ai-research-preview?scope=asset&asset=${id}&q=discharge&search=document&page=2#doc-123`;
  const detail = new URL(documentHref(`/documents/${id}?page=47`, source), 'https://app.invalid');
  assert.equal(detail.searchParams.get('returnTo'), source);
  assert.equal(documentPage(detail.searchParams.get('page'), 355), 47);
  assert.equal(originalDocumentUrl(id, 47), `/api/media/documents/${id}#page=47`);
});
test('invalid physical pages use page one and do not become arbitrary fragments', () => {
  for (const page of [0,-1,1.5,NaN,Infinity]) assert.equal(originalDocumentUrl(id,page), `/api/media/documents/${id}#page=1`);
  assert.equal(documentPage('356',355),1);
  assert.equal(documentPage(['47','2'],355),1);
});
test('unavailable original and temporary network failure remain distinct from evidence absence', () => {
  assert.match(documentMediaError(410), /original file is unavailable.*metadata/i);
  assert.match(documentMediaError(404), /could not be found/);
  assert.match(documentMediaError(503), /connection and retry/);
  assert.doesNotMatch(documentMediaError(500), /no evidence|no data/i);
});

import test from "node:test";
import assert from "node:assert/strict";
import { documentReturnTo, documentHref, documentBackLabel, documentPage } from "../src/lib/document-navigation.ts";

const id = "6c2975db-da89-546c-b1c7-f421827c1fc2";
test("document return links retain origin, filters and anchor across reloads and new tabs", () => {
  for (const origin of ["/ai-research-preview", `/assets/${id}?tab=documents#technical`, `/data-sources/${id}/documents`, "/methodology#coverage", "/map?asset=spillway", `/reservoirs/${id}/3d`]) {
    const href = documentHref(`/documents/${id}`, origin);
    assert.equal(documentReturnTo(new URL(href, "https://app.invalid").searchParams.get("returnTo")), origin);
  }
  assert.equal(documentBackLabel("/ai-research-preview?asset=spillway"), "Back to AI Research");
  assert.equal(documentBackLabel(`/data-sources/${id}/documents`), "Back to source documents");
});

test("untrusted return destinations cannot leave application views or break the detail route", () => {
  for (const bad of [undefined, ["/map", "/methodology"], "https://other.invalid", "//other.invalid/map", "//[", "javascript:alert(1)", "/\\other.invalid", "/api/media/documents/id", "/%2f%2fother.invalid", "/map\n", "/unknown"]) {
    assert.equal(documentReturnTo(bad), null, String(bad));
  }
  assert.equal(documentHref(`/documents/${id}`, "https://other.invalid"), `/documents/${id}`);
});

test("shared asset/source/document drilldowns return through the actual selected workspace", () => {
  const map = `/map?asset=${id}&zoom=13.5&lat=11.32&lng=106.34#selected-asset`;
  const asset = documentHref(`/assets/${id}#record-original`, map);
  const source = documentHref(`/data-sources/${id}/documents`, asset);
  const doc = documentHref(`/documents/${id}?page=47#preview`, source);
  const docUrl = new URL(doc, "https://app.invalid");
  assert.equal(docUrl.searchParams.get('page'), '47');
  assert.equal(docUrl.hash, '#preview');
  assert.equal(documentReturnTo(docUrl.searchParams.get('returnTo')), source);
  assert.equal(documentReturnTo(new URL(source, "https://app.invalid").searchParams.get('returnTo')), asset);
  assert.equal(documentReturnTo(new URL(asset, "https://app.invalid").searchParams.get('returnTo')), map);
  assert.equal(documentBackLabel(asset), 'Back to asset');
  assert.equal(documentBackLabel(`/reservoirs/${id}/3d?model=${id}&object=roof`), 'Back to 3D view');
});

test("target modes, physical pages, anchors and existing query fields survive origin merging", () => {
  const href = documentHref(`/documents/${id}?page=47&download=false#original`, '/ai-research-preview?q=th%E1%BB%A7y+l%E1%BB%B1c&scope=corpus&search=document&page=2');
  const url = new URL(href, 'https://app.invalid');
  assert.equal(url.searchParams.get('page'), '47');
  assert.equal(url.searchParams.get('download'), 'false');
  assert.equal(url.hash, '#original');
  assert.equal(new URL(url.searchParams.get('returnTo'), 'https://app.invalid').searchParams.get('page'), '2');
  assert.equal(documentHref(`/assets/${id}#technical`, `/assets/${id}#sources`), `/assets/${id}#technical`);
});

test("malformed paths, duplicate origins and hidden control characters cannot become return links", () => {
  for (const bad of [
    '/map/../methodology', `/assets/${id}/../${id}`, '/assets/not-a-uuid', '/documents/aaaa',
    '/%6dap', '/map?x=%', '/map?x=%zz', '/map?x=%0a', '/map?x=%5c',
    '/map?returnTo=%2f%2fother.invalid', '/map?returnTo=%2fmethodology&returnTo=%2fmap',
    `/documents/${id}?returnTo=${encodeURIComponent('/map?returnTo=https://other.invalid')}`,
    '/map?' + 'x'.repeat(8192),
  ]) assert.equal(documentReturnTo(bad), null, bad.slice(0, 200));
});

test("repeated nested navigation is bounded while preserving the immediate origin", () => {
  let previous = '/map?asset=' + id;
  for (let n = 0; n < 20; n++) {
    const target = n % 2 ? `/assets/${id}` : `/documents/${id}`;
    const next = documentHref(target, previous);
    assert.ok(next.length <= 8192);
    assert.equal(documentReturnTo(next), next);
    const origin = new URL(next, 'https://app.invalid').searchParams.get('returnTo');
    assert.equal(new URL(origin, 'https://app.invalid').pathname, new URL(previous, 'https://app.invalid').pathname);
    previous = next;
  }
});


test("physical page requests remain one-based and bounded by original metadata", () => {
  assert.equal(documentPage('47', 355), 47);
  for (const page of [undefined, ['47'], '0', '-1', '1.5', '047', '356', '100000', 'NaN']) assert.equal(documentPage(page, 355), 1);
  assert.equal(documentPage('10001', null), 1);
});

test('self-link on a source view retains its previous origin without nesting itself', () => {
  const id = '33333333-3333-4333-8333-333333333333';
  const path = `/data-sources/${id}/documents`;
  const origin = `${path}?returnTo=${encodeURIComponent('/ai-research-preview?q=pressure&scope=corpus&search=document&page=2')}`;
  const target = new URL(documentHref(path,origin),'https://app.invalid');
  assert.equal(target.searchParams.get('returnTo'),'/ai-research-preview?q=pressure&scope=corpus&search=document&page=2');
  assert.equal(documentReturnTo(target.pathname+target.search),target.pathname+target.search);
});

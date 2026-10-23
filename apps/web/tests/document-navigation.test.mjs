import test from "node:test";
import assert from "node:assert/strict";
import { documentReturnTo, documentHref, documentBackLabel } from "../src/lib/document-navigation.ts";

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

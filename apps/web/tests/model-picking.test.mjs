import test from "node:test";
import assert from "node:assert/strict";
import { pickedObjectKey } from "../src/lib/model-picking.ts";

test("Cesium node name is the stable object key, never the asset ID", () => {
  assert.equal(
    pickedObjectKey(
      { id: "model-a", detail: { node: { node: { name: "Gate_01" } } } },
      "model-a",
    ),
    "Gate_01",
  );
});
test("picks from another model do not resolve a same-named node", () => {
  assert.equal(
    pickedObjectKey(
      { id: "model-b", detail: { node: { node: { name: "Gate_01" } } } },
      "model-a",
    ),
    null,
  );
});
for (const pick of [
  undefined,
  null,
  {},
  { id: "model-a" },
  { id: "model-a", detail: { node: { node: { name: "" } } } },
  { id: "model-a", detail: { node: { node: { name: 123 } } } },
]) {
  test(`empty or unsupported pick clears selection: ${JSON.stringify(pick)}`, () => {
    assert.equal(pickedObjectKey(pick, "model-a"), null);
  });
}

// Version-pinned adapter for Cesium 1.146 / engine 26.4.
// PickingPipelineStage emits one pick ID per primitive. Fail closed if internals change.
import type { BoundingSphere } from "cesium";
type PickId = { color: unknown; object: { id?: unknown; instanceId?: unknown; detail?: { node?: { node?: { name?: unknown; instances?: unknown } }; primitive?: { drawCommand?: { boundingVolume?: BoundingSphere } } } } };
export function selectedPrimitives(model: unknown, modelId: string, key: string | null) {
  if (!key || !model || typeof model !== "object") return [];
  const ids = (model as { _pickIds?: PickId[] })._pickIds;
  if (!Array.isArray(ids)) return [];
  const matches = ids.filter(p => p?.color && p.object?.id === modelId && p.object.detail?.node?.node?.name === key);
  // Reused names / instances cannot establish a unique object. Never select the whole model.
  if (!matches.length || new Set(matches.map(p => p.object.detail?.node)).size !== 1 || matches.some(p => p.object.instanceId !== undefined || p.object.detail?.node?.node?.instances)) return [];
  return matches;
}

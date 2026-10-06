// Cesium 1.146 pick adapter. Keep this boundary covered when upgrading Cesium.
export function pickedObjectKey(pick: unknown, modelId: string): string | null {
  if (!pick || typeof pick !== "object") return null;
  const value = pick as {
    id?: unknown;
    detail?: { node?: { node?: { name?: unknown } } };
  };
  if (value.id !== modelId) return null;
  const name = value.detail?.node?.node?.name;
  return typeof name === "string" && name.length > 0 ? name : null;
}

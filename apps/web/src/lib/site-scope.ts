// Single managed reservoir; deployment may override its ID without name-based logic.
export const MANAGED_RESERVOIR_ID = process.env.NEXT_PUBLIC_RESERVOIR_ID ?? "63adca21-9195-44e2-81a2-0475bd6829f3";
// An isolated public-demo deployment serves only the fictional DEMO- corpus,
// always under a visible synthetic-data banner. Research deployments keep RS-.
export const SYNTHETIC_DEMO = process.env.NEXT_PUBLIC_SITE_MODE === "synthetic-demo";
export const RECORD_CODE_PREFIX = SYNTHETIC_DEMO ? "DEMO-" : "RS-";
export const RESERVOIR_HREF = `/reservoirs/${MANAGED_RESERVOIR_ID}`;
export function isManagedReservoir(record: { id: string }) {
  return record.id === MANAGED_RESERVOIR_ID;
}
export function isResearchAsset(record: { asset_code: string; reservoir_id: string }) {
  return record.reservoir_id === MANAGED_RESERVOIR_ID && record.asset_code.startsWith(RECORD_CODE_PREFIX);
}
export function isResearchSource(record: { source_code: string; reservoir_id: string }) {
  return record.reservoir_id === MANAGED_RESERVOIR_ID && record.source_code.startsWith(RECORD_CODE_PREFIX);
}
export function isResearchModel(record: { model_code: string; reservoir_id: string }) {
  return record.reservoir_id === MANAGED_RESERVOIR_ID && record.model_code.startsWith(RECORD_CODE_PREFIX);
}
export function visibleDescription(value: string | null) {
  return value && !/\b(development|synthetic|example|demo|placeholder|seed|mock)\b/i.test(value) ? value : null;
}

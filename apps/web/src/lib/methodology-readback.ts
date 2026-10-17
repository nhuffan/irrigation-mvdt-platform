import type { TechnicalAttribute } from "../types/technical-attribute";
export function technicalReadback(records: TechnicalAttribute[]) {
  return [...records].sort((a, b) => a.id.localeCompare(b.id)).map(t => ({
    id: t.id, key: t.attribute_key, number: t.value_number, text: t.value_text,
    unit: t.unit, verification_status: t.verification_status, source_id: t.source_id,
    level: t.reviewed_provenance?.verification_level ?? null,
    locator: t.reviewed_provenance?.source_locator ?? null,
    source_code: t.reviewed_provenance?.source_code ?? null,
    authority: t.reviewed_provenance?.authority ?? null,
  }));
}
export function sameReadback(actual: unknown, expected: unknown) {
  return JSON.stringify(actual) === JSON.stringify(expected);
}

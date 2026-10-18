import type { MethodologyQuantitative } from "./methodology-quantitative";
/** Public, read-only v2 extension. A legacy snapshot has no completion data. */
export type CompletionMetric = { id: string; label: string; numerator: number | null; denominator: number | null; value: number | null; formula: string; unit: string; scope: string; status: string; captured_at: string; basis: string[]; limitation: string };
type Counts = { applicable: number | null; available: number | null; missing: number | null; not_applicable: number | null; unknown: number | null };
export type MaimRow = Counts & { asset_id: string; asset_code: string; scope: string; parent_asset_code: string; category: string; status: string; proposed: (Counts & { optional: number | null }) | null; fields: { field: string; attribute_key: string; expected_unit: string; requirement: string; review_status: string; observed: string; basis: string }[] };
export type MethodologyCompletion = {
  schema_version: "METHODOLOGY-COMPLETION-v1"; captured_at: string;
  status_definitions: { status: string; definition: string }[];
  study_design: { title: string; design: string; status: string; primary_denominator: number; component_count: number; scope_rationale: string; units: { unit: string; definition: string; scope: string }[]; collection_method: string[]; admission_method: string[] };
  maim: { status: string; basis: string; approval_status: string; rows: MaimRow[]; dictionary?: { defined_entries: number; required_entries: number; status: string; limitation: string } };
  metrics: CompletionMetric[];
  source_quality: { authority: { classification: string; count: number }[]; verification: { classification: string; count: number }[]; review: { classification: string; count: number }[]; dates: { code: string; source_date: string | null; date_status: string }[]; conflicts: { asset_code: string; attribute_key: string; record_ids: string[]; status: string }[] };
  workflow: { id: string; label: string; status: string; evidence: string[]; limitation: string }[];
  retrieval_tasks: { id: string; prompt: string; success_criterion: string; feasibility: string; status: string; basis: string[] }[];
  baseline_protocol: { design: string; status: string; pairing_keys: string[]; timing: string; timeout: string; order_and_training: string; analysis: string; bias: string; participant_count: number | null; observations: number | null; time_results: unknown };
  questionnaire: { instrument: string; status: string; item_count: number; scale: string; analysis: string; results: unknown };
  readiness: { status: string; dataset_status: string; compiler_blocker_count: number; declared_gates: { id: string; label: string; category: string; required: boolean; status: string; decision_owner: string; blocker_group: string }[]; groups: { id: string; unresolved_gate_count: number; gate_ids: string[] }[]; accepted_gate_ids: string[]; not_applicable_gate_ids?: string[]; unresolved_gate_ids: string[]; approval_summary: { approval_type: string; scope: string; required_role: string; status: string }[]; limitation: string };
  provenance: { methodology_package_fingerprint: string; package_status: string; previous_package_fingerprint: string | null; completion_artifact_sha256: string; documents: { id: string; label: string; href: string | null; sha256: string | null; status: string }[] };
  live_readback?: unknown;
  quantitative?: MethodologyQuantitative;
};
const PRIVATE_KEY = /^(?:reviewer(?:_name|_receipt)?|signature|receipt|consent|email|phone|storage_key|local_path|private_path|password|api_key|token)$/i;
/** A defense in depth scrub: exporter projection remains the primary public boundary. */
export function publicResearchText(value: string) {
  return value.replace(/(?:file:\/\/|\/(?:Users|Volumes|home|private|var|tmp)\/|\b[A-Z]:[\\/])[^\s<>"']*/gi, "[private path]")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[private contact]")
    .replace(/([?&](?:key|token|access_token|api_key)=)[^&#\s]*/gi, "$1[redacted]");
}
export function publicResearchValue<T>(value: T): T {
  if (typeof value === "string") return publicResearchText(value) as T;
  if (Array.isArray(value)) return value.map(publicResearchValue) as T;
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).filter(([key]) => !PRIVATE_KEY.test(key)).map(([key, child]) => [key, publicResearchValue(child)])) as T;
  return value;
}
const PUBLIC_DOCUMENT_PATHS = new Set([
  "research/evaluation/protocol.md", "research/evaluation/stage5b_protocol.md", "research/evaluation/retrieval_tasks.md",
  "research/evaluation/questionnaire.md", "research/evaluation/results_outline.md", "research/evaluation/methodology_closure_review.md",
  "research/evaluation/methodology_checkpoint_review.md", "scripts/export_methodology_dashboard.py", "scripts/methodology_completion.py",
]);
export function publicMethodologyLink(value: unknown): string | null {
  if (typeof value !== "string" || /%(?:2e|2f|5c)|\\|\/\.\.?(?:\/|$)/i.test(value)) return null;
  try {
    const u = new URL(value);
    const prefix = "/nhuffan/irrigation-mvdt-platform/blob/main/";
    return u.protocol === "https:" && u.hostname === "github.com" && !u.username && !u.password && !u.search && !u.hash &&
      u.pathname.startsWith(prefix) && PUBLIC_DOCUMENT_PATHS.has(u.pathname.slice(prefix.length)) ? u.href : null;
  } catch { return null; }
}
function object(v: unknown): v is Record<string, unknown> { return !!v && typeof v === "object" && !Array.isArray(v); }
const counts = ["applicable", "available", "missing", "not_applicable", "unknown"] as const;
const validCount = (v: unknown) => v === null || (typeof v === "number" && Number.isInteger(v) && v >= 0);
export function completionFromSnapshot(snapshot: unknown): MethodologyCompletion | null {
  if (!object(snapshot) || snapshot.schema_version !== "METHODOLOGY-DASHBOARD-v2" || !object(snapshot.completion)) return null;
  const c = snapshot.completion;
  if (c.schema_version !== "METHODOLOGY-COMPLETION-v1" || typeof c.captured_at !== "string" ||
    !["study_design", "maim", "source_quality", "baseline_protocol", "questionnaire", "readiness", "provenance"].every(k => object(c[k])) ||
    !["status_definitions", "metrics", "workflow", "retrieval_tasks"].every(k => Array.isArray(c[k]))) return null;
  const maim = c.maim as Record<string, unknown>;
  if (!Array.isArray(maim.rows) || !maim.rows.every(r => object(r) && counts.every(k => validCount(r[k])) && Array.isArray(r.fields) &&
    (r.proposed === null || (object(r.proposed) && [...counts, "optional"].every(k => validCount((r.proposed as Record<string, unknown>)[k])))))) return null;
  const structures = [
    [c.study_design, ["units", "collection_method", "admission_method"]],
    [c.source_quality, ["authority", "verification", "review", "dates", "conflicts"]],
    [c.baseline_protocol, ["pairing_keys"]],
    [c.readiness, ["declared_gates", "groups", "accepted_gate_ids", "unresolved_gate_ids", "approval_summary"]],
    [c.provenance, ["documents"]],
  ] as const;
  if (structures.some(([parent, keys]) => keys.some(key => !Array.isArray((parent as Record<string, unknown>)[key])))) return null;
  const arrays = (parent: unknown, key: string) => (parent as Record<string, unknown>)[key] as unknown[];
  if (!(c.status_definitions as unknown[]).every(v => object(v) && typeof v.status === "string" && typeof v.definition === "string") ||
    !(c.metrics as unknown[]).every(v => object(v) && typeof v.id === "string" && Array.isArray(v.basis)) ||
    !(c.workflow as unknown[]).every(v => object(v) && typeof v.id === "string" && Array.isArray(v.evidence)) ||
    !(c.retrieval_tasks as unknown[]).every(v => object(v) && typeof v.id === "string" && Array.isArray(v.basis)) ||
    !arrays(c.provenance, "documents").every(v => object(v) && typeof v.id === "string" && typeof v.label === "string") ||
    !arrays(c.readiness, "groups").every(v => object(v) && Array.isArray(v.gate_ids)) ||
    !arrays(c.source_quality, "conflicts").every(v => object(v) && Array.isArray(v.record_ids))) return null;
  const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(s => typeof s === "string");
  const texts = (v: unknown, keys: string[]) => object(v) && keys.every(k => typeof v[k] === "string");
  const all = (parent: unknown, key: string, test: (v: unknown) => boolean) => arrays(parent, key).every(test);
  const nullableText = (v: unknown) => v === null || typeof v === "string";
  const nullableNumber = (v: unknown) => v === null || (typeof v === "number" && Number.isFinite(v));
  if (!texts(c.study_design, ["title", "design", "status", "scope_rationale"]) ||
    !all(c.study_design, "units", v => texts(v, ["unit", "definition", "scope"])) ||
    !["collection_method", "admission_method"].every(k => strings((c.study_design as Record<string, unknown>)[k])) ||
    !texts(c.maim, ["status", "basis", "approval_status"]) ||
    !maim.rows.every(v => texts(v, ["asset_id", "asset_code", "scope", "category", "status"]) && (v as Record<string, unknown>).fields instanceof Array &&
      ((v as Record<string, unknown>).fields as unknown[]).every(f => texts(f, ["field", "attribute_key", "requirement", "review_status", "observed", "basis"]) && nullableText((f as Record<string, unknown>).expected_unit))) ||
    !(c.metrics as unknown[]).every(v => texts(v, ["id", "label", "formula", "unit", "scope", "status", "captured_at", "limitation"]) && object(v) && strings(v.basis) && ["numerator", "denominator", "value"].every(k => nullableNumber(v[k]))) ||
    !["authority", "verification", "review"].every(k => all(c.source_quality, k, v => texts(v, ["classification"]) && object(v) && validCount(v.count) && v.count !== null)) ||
    !all(c.source_quality, "dates", v => texts(v, ["code", "date_status"]) && object(v) && nullableText(v.source_date)) ||
    !all(c.source_quality, "conflicts", v => texts(v, ["asset_code", "attribute_key", "status"]) && object(v) && strings(v.record_ids)) ||
    !(c.workflow as unknown[]).every(v => texts(v, ["id", "label", "status", "limitation"]) && object(v) && strings(v.evidence)) ||
    !(c.retrieval_tasks as unknown[]).every(v => texts(v, ["id", "prompt", "success_criterion", "feasibility", "status"]) && object(v) && strings(v.basis)) ||
    !texts(c.baseline_protocol, ["design", "status", "timing", "timeout", "order_and_training", "analysis", "bias"]) ||
    !strings((c.baseline_protocol as Record<string, unknown>).pairing_keys) ||
    !texts(c.questionnaire, ["instrument", "status", "scale", "analysis"]) ||
    !validCount((c.questionnaire as Record<string, unknown>).item_count) || (c.questionnaire as Record<string, unknown>).item_count === null ||
    !texts(c.readiness, ["status", "dataset_status", "limitation"]) ||
    !validCount((c.readiness as Record<string, unknown>).compiler_blocker_count) || (c.readiness as Record<string, unknown>).compiler_blocker_count === null ||
    ((c.readiness as Record<string, unknown>).not_applicable_gate_ids !== undefined && !strings((c.readiness as Record<string, unknown>).not_applicable_gate_ids)) ||
    (maim.dictionary !== undefined && (!texts(maim.dictionary, ["status", "limitation"]) || !object(maim.dictionary) ||
      !["defined_entries", "required_entries"].every(k => validCount((maim.dictionary as Record<string, unknown>)[k]) && (maim.dictionary as Record<string, unknown>)[k] !== null))) ||
    !all(c.readiness, "declared_gates", v => texts(v, ["id", "label", "category", "status", "decision_owner", "blocker_group"]) && object(v) && typeof v.required === "boolean") ||
    !all(c.readiness, "groups", v => texts(v, ["id"]) && object(v) && validCount(v.unresolved_gate_count) && v.unresolved_gate_count !== null && strings(v.gate_ids)) ||
    !["accepted_gate_ids", "unresolved_gate_ids"].every(k => strings((c.readiness as Record<string, unknown>)[k])) ||
    !all(c.readiness, "approval_summary", v => texts(v, ["approval_type", "scope", "required_role", "status"])) ||
    !texts(c.provenance, ["methodology_package_fingerprint", "package_status", "completion_artifact_sha256"]) ||
    !nullableText((c.provenance as Record<string, unknown>).previous_package_fingerprint) ||
    !all(c.provenance, "documents", v => texts(v, ["id", "label", "status"]) && object(v) && nullableText(v.href) && nullableText(v.sha256))) return null;
  // Only these reviewed exporter sections are public. Never spread arbitrary future extensions.
  const safe = publicResearchValue(Object.fromEntries(["schema_version", "captured_at", "status_definitions", "study_design", "maim", "metrics", "source_quality", "workflow", "retrieval_tasks", "baseline_protocol", "questionnaire", "readiness", "provenance"].map(k => [k, c[k]]))) as MethodologyCompletion;
  safe.readiness.declared_gates = safe.readiness.declared_gates.map(g => ({ ...g,
    decision_owner: typeof g.decision_owner === "string" && /^[A-Z_ /,-]+$/.test(g.decision_owner) ? g.decision_owner : "ROLE_UNAVAILABLE",
  }));
  safe.provenance.documents = safe.provenance.documents.map(d => ({ id: d.id, label: d.label, href: publicMethodologyLink(d.href), sha256: d.sha256, status: d.status }));
  // Participant results are intentionally not part of this content-only adapter.
  safe.baseline_protocol.participant_count = null; safe.baseline_protocol.observations = null; safe.baseline_protocol.time_results = null;
  safe.questionnaire.results = null;
  return safe;
}
export function snapshotVersionSupported(snapshot: { schema_version?: unknown }) {
  return ["METHODOLOGY-DASHBOARD-v1", "METHODOLOGY-DASHBOARD-v2"].includes(String(snapshot.schema_version));
}
/** Compare structured readback regardless of object-key insertion order; null is never zero. */
export function stableReadback(value: unknown): string {
  const sort = (v: unknown): unknown => Array.isArray(v) ? v.map(sort) : object(v) ? Object.fromEntries(Object.keys(v).sort().map(k => [k, sort(v[k])])) : v;
  return JSON.stringify(sort(value));
}

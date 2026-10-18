import { publicResearchText } from "./methodology-completion.ts";
type Count = number | null;
export type QuantitativeMetricResult = { metric_id: string; numerator: Count; denominator: Count; value: number | null; status: string };
type ProposedMaim = { applicable: Count; present: Count; verified_record: Count; missing: Count; not_applicable: Count; unknown: Count; optional: Count };
export type QuantitativeAssetCoverage = { asset_id: string; asset_code: string; scope: string; parent_asset_code: string; direct_l2: Count; descendant_l2: Count; maim: { status: string; applicable: Count; present: Count; verified_record: Count; missing: Count; not_applicable: Count; proposed: ProposedMaim | null; proposed_semantics?: string; proposed_not_applicable?: { field: string; reason: string; basis: string }[] }; metrics: QuantitativeMetricResult[] };
export type FieldQualityCounts = { total_fields: Count; numeric_fields: Count; text_fields: Count; both_value_fields: Count; missing_value_fields: Count; unit_present: Count; unit_missing: Count; unit_text: Count; locator_present: Count; locator_missing: Count; source_linked: Count; source_missing: Count };
export type MethodologyQuantitative = {
  schema_version: "METHODOLOGY-QUANTITATIVE-v1";
  temporal_basis: { snapshot_captured_at: string; api_read_at: string | null; dataset_as_of: string | null; dataset_status: string; rule: string };
  metric_dictionary: { id: string; name: string; definition: string; numerator_rule: string; denominator_rule: string; missing_rule: string; na_rule: string; temporal_basis: string; scope_policy: string; result_reference?: string; basis_docs: string[] }[];
  coverage: { groups: { scope: string; asset_count: Count; direct_l2: Count; descendant_l2: Count; metrics: QuantitativeMetricResult[] }[]; assets: QuantitativeAssetCoverage[] };
  field_quality: FieldQualityCounts & { units: { value: string; count: Count }[]; source_status: { value: string; count: Count }[]; source_review_status: { value: string; count: Count }[]; semantics: { value: string; count: Count }[];
    by_asset: (FieldQualityCounts & { asset_id: string; asset_code: string; category_code: string; scope: string })[];
    by_category: { category_code: string; total_fields: Count; numeric_fields: Count; text_fields: Count; missing_value_fields: Count }[] };
  lineage: { asset_id: string; asset_code: string; source_id: string | null; source_code: string | null; field_count: Count; attribute_keys: string[]; locators: string[]; field_locators?: { attribute_key: string; locators: string[] }[]; retained_document_records: Count; linked_document_records: Count; availability: string; asset_href: string | null; source_href: string | null; documents: { id: string; href: string | null; checksum_sha256: string | null }[] }[];
  retained_review_blockers: { id: string; label: string; basis_file: string; entry_count: Count; status_counts: { status: string; count: Count }[]; limitation: string }[];
  retrieval_feasibility: { asset_id: string; asset_code: string; scope: string; task_id: string; evidence_status: string; available_records: Count; answer_key_status: string; reason: string; asset_href: string | null }[];
  empirical_metrics: { id: string; name: string; formula: string; numerator_rule: string; denominator_rule: string; missing_rule: string; selection_bias: string; status: string; results: null }[];
  readiness_groups: { id: string; finding_count: Count; status: string }[];
  source_dates?: { source_code: string; date_kind: string; date_value: string | null; status: string; basis: string }[];
  source_ages?: { source_id: string; source_code: string; source_date: string | null; age_days: number | null; status: string }[];
  input_hashes: Record<string, string>;
};
export type QuantitativeExtension = { status: "AVAILABLE"; data: MethodologyQuantitative } | { status: "UNAVAILABLE" | "INVALID_EXTENSION"; data: null };
const obj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
const str = (v: unknown): v is string => typeof v === "string";
const count = (v: unknown): v is Count => v === null || (typeof v === "number" && Number.isInteger(v) && v >= 0);
const num = (v: unknown) => v === null || (typeof v === "number" && Number.isFinite(v));
const strs = (v: unknown): v is string[] => Array.isArray(v) && v.every(str);
const nullableStr = (v: unknown) => v === null || str(v);
const fields = (v: unknown, names: readonly string[], check: (v: unknown) => boolean) => obj(v) && names.every(k => check(v[k]));
const rows = (v: unknown, check: (v: unknown) => boolean): v is Record<string, unknown>[] => Array.isArray(v) && v.every(check);
const metric = (v: unknown) => fields(v, ["metric_id", "status"], str) && fields(v, ["numerator", "denominator"], count) && obj(v) && num(v.value);
const qualityKeys = ["total_fields", "numeric_fields", "text_fields", "both_value_fields", "missing_value_fields", "unit_present", "unit_missing", "unit_text", "locator_present", "locator_missing", "source_linked", "source_missing"] as const;
const maimKeys = ["applicable", "present", "verified_record", "missing", "not_applicable"] as const;
const uuid = (id: unknown) => str(id) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
export function quantitativeLink(kind: "asset" | "source" | "document", id: unknown): string | null {
  return uuid(id) ? kind === "asset" ? `/assets/${id}` : kind === "source" ? `/data-sources/${id}/documents` : `/documents/${id}` : null;
}
/** An optional content extension is validated independently of the legacy completion. */
export function quantitativeFromSnapshot(snapshot: unknown): QuantitativeExtension {
  if (!obj(snapshot) || !obj(snapshot.completion) || snapshot.completion.quantitative === undefined) return { status: "UNAVAILABLE", data: null };
  const q = snapshot.completion.quantitative;
  const invalid: QuantitativeExtension = { status: "INVALID_EXTENSION", data: null };
  if (!obj(q) || q.schema_version !== "METHODOLOGY-QUANTITATIVE-v1" || !obj(q.temporal_basis) || !obj(q.coverage) || !obj(q.field_quality) || !obj(q.input_hashes)) return invalid;
  if (!fields(q.temporal_basis, ["snapshot_captured_at", "dataset_status", "rule"], str) || !fields(q.temporal_basis, ["api_read_at", "dataset_as_of"], nullableStr) ||
    !rows(q.metric_dictionary, d => fields(d, ["id", "name", "definition", "numerator_rule", "denominator_rule", "missing_rule", "na_rule", "temporal_basis", "scope_policy"], str) && obj(d) && strs(d.basis_docs) && (d.result_reference === undefined || str(d.result_reference))) ||
    !rows(q.coverage.groups, g => fields(g, ["scope"], str) && fields(g, ["asset_count", "direct_l2", "descendant_l2"], count) && obj(g) && rows(g.metrics, metric)) ||
    !rows(q.coverage.assets, a => fields(a, ["asset_id", "asset_code", "scope", "parent_asset_code"], str) && fields(a, ["direct_l2", "descendant_l2"], count) && obj(a) && rows(a.metrics, metric) && obj(a.maim) && str(a.maim.status) && fields(a.maim, maimKeys, count) && (a.maim.proposed === null || fields(a.maim.proposed, [...maimKeys, "unknown", "optional"], count)) && (a.maim.proposed_semantics === undefined || str(a.maim.proposed_semantics)) && (a.maim.proposed_not_applicable === undefined || rows(a.maim.proposed_not_applicable, r => fields(r, ["field", "reason", "basis"], str)))) ||
    !fields(q.field_quality, qualityKeys, count) || !["units", "source_status", "source_review_status", "semantics"].every(k => rows((q.field_quality as Record<string, unknown>)[k], v => fields(v, ["value"], str) && fields(v, ["count"], count))) ||
    !rows(q.field_quality.by_asset, a => fields(a, ["asset_id", "asset_code", "category_code", "scope"], str) && fields(a, qualityKeys, count)) ||
    !rows(q.field_quality.by_category, a => fields(a, ["category_code"], str) && fields(a, ["total_fields", "numeric_fields", "text_fields", "missing_value_fields"], count)) ||
    !rows(q.lineage, l => fields(l, ["asset_id", "asset_code", "availability"], str) && fields(l, ["source_id", "source_code"], nullableStr) && fields(l, ["field_count", "retained_document_records", "linked_document_records"], count) && obj(l) && strs(l.attribute_keys) && strs(l.locators) && (l.field_locators === undefined || rows(l.field_locators, f => fields(f, ["attribute_key"], str) && obj(f) && strs(f.locators))) && rows(l.documents, d => fields(d, ["id"], str) && obj(d) && nullableStr(d.checksum_sha256))) ||
    !rows(q.retained_review_blockers, b => fields(b, ["id", "label", "basis_file", "limitation"], str) && fields(b, ["entry_count"], count) && obj(b) && rows(b.status_counts, s => fields(s, ["status"], str) && fields(s, ["count"], count))) ||
    !rows(q.retrieval_feasibility, r => fields(r, ["asset_id", "asset_code", "scope", "task_id", "evidence_status", "answer_key_status", "reason"], str) && fields(r, ["available_records"], count)) ||
    !rows(q.empirical_metrics, e => fields(e, ["id", "name", "formula", "numerator_rule", "denominator_rule", "missing_rule", "selection_bias", "status"], str) && obj(e) && e.results === null) ||
    !rows(q.readiness_groups, r => fields(r, ["id", "status"], str) && fields(r, ["finding_count"], count)) ||
    (q.source_dates !== undefined && !rows(q.source_dates, d => fields(d, ["source_code", "date_kind", "status", "basis"], str) && obj(d) && nullableStr(d.date_value))) ||
    (q.source_ages !== undefined && !rows(q.source_ages, d => fields(d, ["source_id", "source_code", "status"], str) && obj(d) && nullableStr(d.source_date) && num(d.age_days)))) return invalid;
  const cleanText = (v: unknown) => publicResearchText(v as string);
  const project = (v: Record<string, unknown>, textKeys: readonly string[], countKeys: readonly string[] = []) => Object.fromEntries([...textKeys.map(k => [k, cleanText(v[k])]), ...countKeys.map(k => [k, v[k]])]);
  const metrics = (v: unknown) => (v as Record<string, unknown>[]).map(m => ({ ...project(m, ["metric_id", "status"], ["numerator", "denominator", "value"]) }));
  const nullableText = (v: unknown) => v === null ? null : cleanText(v);
  const temporal = q.temporal_basis;
  const quality = q.field_quality;
  // Explicit field projection keeps receipts, originals, private paths and future unknown keys out.
  const data = {
    schema_version: q.schema_version,
    temporal_basis: { ...project(temporal, ["snapshot_captured_at", "dataset_status", "rule"]), api_read_at: nullableText(temporal.api_read_at), dataset_as_of: nullableText(temporal.dataset_as_of) },
    metric_dictionary: q.metric_dictionary.map(d => ({ ...project(d, ["id", "name", "definition", "numerator_rule", "denominator_rule", "missing_rule", "na_rule", "temporal_basis", "scope_policy"]), basis_docs: (d.basis_docs as string[]).map(cleanText), ...(d.result_reference === undefined ? {} : { result_reference:cleanText(d.result_reference) }) })),
    coverage: { groups: q.coverage.groups.map(g => ({ ...project(g, ["scope"], ["asset_count", "direct_l2", "descendant_l2"]), metrics: metrics(g.metrics) })),
      assets: q.coverage.assets.map(a => { const m = a.maim as Record<string, unknown>; return { ...project(a, ["asset_id", "asset_code", "scope", "parent_asset_code"], ["direct_l2", "descendant_l2"]), metrics: metrics(a.metrics), maim: { ...project(m, ["status"], maimKeys), proposed: m.proposed === null ? null : project(m.proposed as Record<string, unknown>, [], [...maimKeys, "unknown", "optional"]), ...(m.proposed_semantics === undefined ? {} : { proposed_semantics:cleanText(m.proposed_semantics) }), ...(m.proposed_not_applicable === undefined ? {} : { proposed_not_applicable: (m.proposed_not_applicable as Record<string, unknown>[]).map(r => project(r, ["field", "reason", "basis"])) }) } }; }) },
    field_quality: { ...project(quality, [], qualityKeys), ...Object.fromEntries(["units", "source_status", "source_review_status", "semantics"].map(k => [k, (quality[k] as Record<string, unknown>[]).map(v => project(v, ["value"], ["count"]))])),
      by_asset: (quality.by_asset as Record<string, unknown>[]).map(a => project(a, ["asset_id", "asset_code", "category_code", "scope"], qualityKeys)), by_category: (quality.by_category as Record<string, unknown>[]).map(a => project(a, ["category_code"], ["total_fields", "numeric_fields", "text_fields", "missing_value_fields"])) },
    lineage: q.lineage.map(l => ({ ...project(l, ["asset_id", "asset_code", "availability"], ["field_count", "retained_document_records", "linked_document_records"]), source_id: nullableText(l.source_id), source_code: nullableText(l.source_code), attribute_keys: (l.attribute_keys as string[]).map(cleanText), locators: (l.locators as string[]).map(cleanText), ...(l.field_locators === undefined ? {} : { field_locators: (l.field_locators as Record<string, unknown>[]).map(f => ({ attribute_key:cleanText(f.attribute_key), locators:(f.locators as string[]).map(cleanText) })) }), asset_href: quantitativeLink("asset", l.asset_id), source_href: quantitativeLink("source", l.source_id), documents: (l.documents as Record<string, unknown>[]).map(d => ({ id:cleanText(d.id), href:quantitativeLink("document", d.id), checksum_sha256:nullableText(d.checksum_sha256) })) })),
    retained_review_blockers: q.retained_review_blockers.map(b => ({ ...project(b, ["id", "label", "basis_file", "limitation"], ["entry_count"]), status_counts: (b.status_counts as Record<string, unknown>[]).map(s => project(s, ["status"], ["count"])) })),
    retrieval_feasibility: q.retrieval_feasibility.map(r => ({ ...project(r, ["asset_id", "asset_code", "scope", "task_id", "evidence_status", "answer_key_status", "reason"], ["available_records"]), asset_href:quantitativeLink("asset", r.asset_id) })),
    empirical_metrics: q.empirical_metrics.map(e => ({ ...project(e, ["id", "name", "formula", "numerator_rule", "denominator_rule", "missing_rule", "selection_bias", "status"]), results:null })),
    readiness_groups: q.readiness_groups.map(r => project(r, ["id", "status"], ["finding_count"])),
    ...(q.source_dates === undefined ? {} : { source_dates: (q.source_dates as Record<string, unknown>[]).map(d => ({ ...project(d, ["source_code", "date_kind", "status", "basis"]), date_value:nullableText(d.date_value) })) }),
    ...(q.source_ages === undefined ? {} : { source_ages: (q.source_ages as Record<string, unknown>[]).map(d => ({ ...project(d, ["source_id", "source_code", "status"], ["age_days"]), source_date:nullableText(d.source_date) })) }),
    input_hashes: Object.fromEntries(Object.entries(q.input_hashes).filter(([name, value]) => /^[A-Za-z0-9_.-]+$/.test(name) && str(value) && /^[a-f0-9]{64}$/i.test(value))),
  } as unknown as MethodologyQuantitative;
  return { status: "AVAILABLE", data };
}

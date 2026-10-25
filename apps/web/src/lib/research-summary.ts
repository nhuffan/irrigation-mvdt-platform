import "server-only";
import snapshot from "@/data/methodology.json";
import { workflowFromResponse, workflowExportAlignment, type WorkflowResult } from "./research-workflow";
import { getReservoirAssets, getSourceDocuments, getModels, getResearchSource } from "./api";
import type { ExplorerRecords } from "./explorer-data";
import { getExplorerData } from "./explorer-data";
import { MANAGED_RESERVOIR_ID } from "./site-scope";
import { coverageRows, coverageTotals } from "./methodology-coverage";
import { assetDisplayName } from "./asset-display";
import { technicalReadback, sameReadback } from "./methodology-readback";
import { evidenceDisplayText } from "./evidence-display";
import { completionFromSnapshot, snapshotVersionSupported, publicResearchValue } from "./methodology-completion";
import { completionReadback, completionAlignment } from "./methodology-observations";
import { quantitativeFromSnapshot } from "./methodology-quantitative";

export async function getResearchSummary() {
  const controlled = snapshot;
  if (controlled.reservoir_id !== MANAGED_RESERVOIR_ID || !snapshotVersionSupported(controlled)) {
    throw new Error("Controlled summary does not match the managed site");
  }
  const workflowPromise: Promise<WorkflowResult> = fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"}/research/workflow`, {
    cache: "no-store", signal: AbortSignal.timeout(15000),
  }).then(async response => response.ok ? workflowFromResponse(await response.json(), MANAGED_RESERVOIR_ID) : {status:"UNAVAILABLE",data:null} as const).catch(() => ({status:"UNAVAILABLE",data:null} as const));
  const assets = await getReservoirAssets(MANAGED_RESERVOIR_ID);
  const records: ExplorerRecords = Object.fromEntries(await Promise.all(assets.map(async a => [a.id, await getExplorerData(a.id)])));
  const rows = coverageRows(assets, records).map(row => ({ ...row,
    category: assets.find(a => a.id === row.id)?.category.code ?? "UNKNOWN",
    name: assetDisplayName({ asset_code: row.code, name: row.name }),
    technical: records[row.id]?.technical?.filter(t => t.reviewed_provenance?.verification_level === "L2").map(t => ({
      id: t.id, key: t.attribute_key, label: evidenceDisplayText(t.attribute_label),
      value: t.value_number ?? (t.value_text === null ? null : evidenceDisplayText(t.value_text)),
      unit: t.unit, verification_status: t.verification_status,
      source_id: t.source_id, source_code: t.reviewed_provenance!.source_code,
      locator: t.reviewed_provenance!.source_locator, authority: t.reviewed_provenance!.authority,
      semantics: "SOURCE_REPORTED / HISTORICAL_DOCUMENTED",
    })) ?? null,
  }));
  // Source inventory totals are controlled snapshot metrics; resolve links against the live API.
  const sources = await Promise.all(controlled.sources.map(async source => {
    if (!source.id) return { ...source, link_available: false, live_document_records: null, live_source: null };
    try {
      const [docs, live] = await Promise.all([getSourceDocuments(source.id), getResearchSource(source.id)]);
      return { ...source, link_available: true, live_document_records: docs.length, live_source: {
        id: live.id, source_code: live.source_code, title: live.title, source_type: live.source_type, source_date: live.source_date,
        authority_level: live.authority_level, verification_status: live.verification_status,
      } };
    } catch { return { ...source, link_available: false, live_document_records: null, live_source: null }; }
  }));
  const models = await getModels(MANAGED_RESERVOIR_ID).catch(() => null);
  const drift = rows.length !== controlled.assets.length || rows.some(row => {
    const expected = controlled.assets.find(a => a.asset_id === row.id);
    const record = records[row.id];
    return !expected || row.direct_l2 !== expected.technical_l2 || row.verified_om !== expected.verified_om_records ||
      row.location !== expected.location_status || row.canonical_geometry !== expected.canonical_geometry_present ||
      row.links !== expected.representative_3d_links || row.condition !== expected.verified_current_condition ||
      row.parent_id !== (controlled.assets.find(a => a.asset_code === expected.parent_asset_code)?.asset_id ?? null) ||
      !sameReadback(record?.technical ? technicalReadback(record.technical) : null, expected.technical_readback) ||
      JSON.stringify(record?.documents?.map(d => d.id).sort()) !== JSON.stringify(expected.document_ids);
  });
  const completion = completionFromSnapshot(controlled);
  const quantitative = quantitativeFromSnapshot(controlled);
  if (completion && quantitative.status === "AVAILABLE") completion.quantitative = quantitative.data;
  const extendedAlignment = completionAlignment(controlled, completionReadback(assets, records, models, sources.filter(s => s.id).some(s => s.live_source === null) ? null : sources.flatMap(s => s.live_source ? [s.live_source] : [])));
  const publicControlled = publicResearchValue({
    schema_version: controlled.schema_version, dataset_version: controlled.dataset_version, reservoir_id: controlled.reservoir_id,
    captured_at: controlled.captured_at, database_fingerprint: controlled.database_fingerprint, methodology: controlled.methodology,
    documents: controlled.documents, protocol: controlled.protocol, assets: controlled.assets, sources: controlled.sources,
    evaluation: controlled.evaluation, input_hashes: controlled.input_hashes, protocol_hashes: controlled.protocol_hashes,
    exporter: controlled.exporter, exporter_sha256: controlled.exporter_sha256,
  });
  return {
    workflow: await workflowPromise,
    export_alignment: workflowExportAlignment(models === null || sources.some(s=>s.id && !s.link_available) || Object.values(records).some(r=>r.technical === null || r.documents === null || r.events === null || r.links === null || r.conditionError), drift || extendedAlignment === "DIFFERENT_OR_UNAVAILABLE"),
    controlled: publicControlled, completion, quantitative_status: quantitative.status, completion_alignment: extendedAlignment, read_at: new Date().toISOString(), rows: publicResearchValue(rows), totals: coverageTotals(rows), sources: publicResearchValue(sources),
    controlled_alignment: drift || extendedAlignment === "DIFFERENT_OR_UNAVAILABLE" ? "DIFFERENT_OR_UNAVAILABLE" : "RECORD_READBACK_MATCH",
    // No raw source notes, receipts, storage keys or reviewer metadata crosses this adapter.
    model_count: models?.length ?? null,
    unique_linked_documents: rows.some(r => r.documents === null || r.unique_files === null) ? null :
      new Set(Object.values(records).flatMap(r => r.documents?.map(d => d.checksum_sha256) ?? [])).size,
  };
}

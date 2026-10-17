import "server-only";
import controlled from "@/data/methodology.json";
import { getReservoirAssets, getSourceDocuments, getModels } from "./api";
import type { ExplorerRecords } from "./explorer-data";
import { getExplorerData } from "./explorer-data";
import { MANAGED_RESERVOIR_ID } from "./site-scope";
import { coverageRows, coverageTotals } from "./methodology-coverage";
import { assetDisplayName } from "./asset-display";
import { technicalReadback, sameReadback } from "./methodology-readback";
import { evidenceDisplayText } from "./evidence-display";

export async function getResearchSummary() {
  if (controlled.reservoir_id !== MANAGED_RESERVOIR_ID || controlled.schema_version !== "METHODOLOGY-DASHBOARD-v1") {
    throw new Error("Controlled summary does not match the managed site");
  }
  const assets = await getReservoirAssets(MANAGED_RESERVOIR_ID);
  const records: ExplorerRecords = Object.fromEntries(await Promise.all(assets.map(async a => [a.id, await getExplorerData(a.id)])));
  const rows = coverageRows(assets, records).map(row => ({ ...row,
    name: assetDisplayName({ asset_code: row.code, name: row.name }),
    technical: records[row.id]?.technical?.filter(t => t.reviewed_provenance?.verification_level === "L2").map(t => ({
      id: t.id, key: t.attribute_key, label: evidenceDisplayText(t.attribute_label),
      value: t.value_number ?? (t.value_text ? evidenceDisplayText(t.value_text) : null),
      unit: t.unit === "text" ? null : t.unit,
      source_id: t.source?.id ?? null, source_code: t.reviewed_provenance!.source_code,
      locator: t.reviewed_provenance!.source_locator, authority: t.reviewed_provenance!.authority,
      semantics: "SOURCE_REPORTED / HISTORICAL_DOCUMENTED",
    })) ?? null,
  }));
  // Source inventory totals are controlled snapshot metrics; resolve links against the live API.
  const sources = await Promise.all(controlled.sources.map(async source => {
    if (!source.id) return { ...source, link_available: false, live_document_records: null };
    try {
      const docs = await getSourceDocuments(source.id);
      return { ...source, link_available: true, live_document_records: docs.length };
    } catch { return { ...source, link_available: false, live_document_records: null }; }
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
  return {
    controlled, read_at: new Date().toISOString(), rows, totals: coverageTotals(rows), sources,
    controlled_alignment: drift ? "DIFFERENT_OR_UNAVAILABLE" : "RECORD_READBACK_MATCH",
    // No raw source notes, receipts, storage keys or reviewer metadata crosses this adapter.
    model_count: models?.length ?? null,
    unique_linked_documents: rows.some(r => r.documents === null) ? null :
      new Set(Object.values(records).flatMap(r => r.documents?.map(d => d.checksum_sha256) ?? [])).size,
  };
}

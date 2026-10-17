import type { Asset } from "../types/asset";
import type { ExplorerRecords } from "./explorer-data";
import { descendantIds, l2Count } from "./asset-hierarchy.ts";

export function knownSum(values: (number | null)[]): number | null {
  return values.some(v => v === null) ? null : (values as number[]).reduce((a, b) => a + b, 0);
}
export function coverageRows(assets: Asset[], records: ExplorerRecords) {
  const technical = Object.fromEntries(assets.map(a => [a.id, records[a.id]?.technical ?? null]));
  return assets.map(asset => {
    const record = records[asset.id];
    const descendants = descendantIds(assets, asset.id);
    const documents = record?.documents;
    return {
      id: asset.id, code: asset.asset_code, name: asset.name, parent_id: asset.parent_asset_id,
      direct_l2: l2Count([asset.id], technical), descendant_l2: l2Count(descendants, technical),
      verified_om: record?.events?.length ?? null,
      documents: documents == null ? null : documents.length,
      unique_files: documents == null ? null : new Set(documents.map(d => d.checksum_sha256)).size,
      links: record?.links?.length ?? null,
      condition: record?.conditionError || !record ? null : record.condition?.verification_status === "VERIFIED" ? 1 : 0,
      location: asset.location?.location_status ?? "UNKNOWN",
      canonical_geometry: asset.geometry === undefined ? null : asset.geometry === null ? 0 : 1,
    };
  });
}
export function coverageTotals(rows: ReturnType<typeof coverageRows>) {
  return {
    primary: rows.filter(r => !r.parent_id).length, components: rows.filter(r => r.parent_id).length, all: rows.length,
    primary_l2: knownSum(rows.filter(r => !r.parent_id).map(r => r.direct_l2)),
    component_l2: knownSum(rows.filter(r => r.parent_id).map(r => r.direct_l2)),
    all_l2: knownSum(rows.map(r => r.direct_l2)), verified_om: knownSum(rows.map(r => r.verified_om)),
    reference_points: rows.filter(r => r.location === "REFERENCE_LOCATION").length,
    canonical_geometry: knownSum(rows.map(r => r.canonical_geometry)),
  };
}

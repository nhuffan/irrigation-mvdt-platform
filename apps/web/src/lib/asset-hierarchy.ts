import type { Asset } from "../types/asset";
import type { TechnicalAttribute } from "../types/technical-attribute";
export type TechnicalRecords = Record<string, TechnicalAttribute[] | null>;
export function descendantIds(assets: Asset[], id: string): string[] {
  const seen = new Set([id]);
  const visit = (parent: string) => {
    for (const asset of assets.filter(a => a.parent_asset_id === parent)) {
      if (!seen.has(asset.id)) { seen.add(asset.id); visit(asset.id); }
    }
  };
  visit(id);
  return [...seen].filter(key => key !== id);
}
export function l2Count(ids: string[], records: TechnicalRecords): number | null {
  if (ids.some(id => records[id] == null)) return null;
  return ids.reduce((sum, id) => sum + records[id]!.filter(r => r.reviewed_provenance?.verification_level === "L2").length, 0);
}
export function hierarchyCoverage(assets: Asset[], records: TechnicalRecords) {
  return {
    primary: l2Count(assets.filter(a => !a.parent_asset_id).map(a => a.id), records),
    components: l2Count(assets.filter(a => a.parent_asset_id).map(a => a.id), records),
    all: l2Count(assets.map(a => a.id), records),
  };
}

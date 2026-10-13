import type { Asset } from "../types/asset";
import type { ExplorerData, ExplorerRecords } from "./explorer-data";
export function dataset(asset: Asset) {
  return asset.asset_code.startsWith("RS-") ? "research" : asset.asset_code.startsWith("DEV-") ? "development" : "other";
}
export function selectedAsset(assets: Asset[], id: string | null) {
  return assets.find(a => a.id === id);
}
export function filterAssets(assets: Asset[], scope: string, geometryOnly: boolean, modelOnly: boolean, records: ExplorerRecords) {
  return assets.filter(a => dataset(a) === scope && (!geometryOnly || a.geometry !== null) && (!modelOnly || !!records[a.id]?.links?.length));
}
export function recordTotal(assets: Asset[], records: ExplorerRecords, key: "technical" | "events" | "links") {
  return assets.some(a => records[a.id]?.[key] == null) ? null : assets.reduce((n,a) => n + (records[a.id][key]?.length ?? 0), 0);
}
export function reviewedPreview(data: ExplorerData) {
  return data.technical?.filter(t => t.reviewed_provenance).slice(0, 3);
}
export function modelHref(asset: Asset, link: NonNullable<ExplorerData["links"]>[number]) {
  return `/reservoirs/${asset.reservoir_id}/3d?model=${encodeURIComponent(link.model_id)}&object=${encodeURIComponent(link.object_key)}`;
}

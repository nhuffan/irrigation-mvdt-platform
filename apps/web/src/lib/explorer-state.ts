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

export function explorerFilters(params: Pick<URLSearchParams, "get">) {
  const location = params.get("location");
  return { query: (params.get("q") ?? "").slice(0, 200), type: params.get("type") ?? "",
    location: ["VERIFIED_GEOMETRY", "REFERENCE_LOCATION", "NO_LOCATION", "CANDIDATE_NEEDS_REVIEW", "CONFLICTED", "UNRESOLVED", "NO_DEFENSIBLE_LOCATION"].includes(location ?? "") ? location! : "all",
    contextVisible: params.get("context") !== "0", modelOnly: params.get("modelOnly") === "1" };
}
export function explorerFilterUrl(href: string, key: "q" | "type" | "location" | "context" | "modelOnly", value: string) {
  const url = new URL(href);
  if (!value || (key === "location" && value === "all") || (key === "context" && value === "1") || (key === "modelOnly" && value === "0")) url.searchParams.delete(key);
  else url.searchParams.set(key, key === "q" ? value.slice(0, 200) : value);
  return url.pathname + url.search + url.hash;
}

import type { Asset, AssetLocation } from "../types/asset";

// Older API responses may expose geometry without a spatial review. Never infer verified.
export function assetLocation(asset: Asset): AssetLocation {
  return asset.location ?? {
    location_status: asset.geometry ? "REFERENCE_LOCATION" : "NO_LOCATION",
    geometry: asset.geometry,
    geometry_type: asset.geometry?.type ?? null,
    crs: asset.geometry ? "EPSG:4326" : null,
    source: asset.geometry ? "Asset registry geometry (unreviewed)" : null,
    locator: null, evidence_id: null, reviewer: null, reviewed_at: null,
    review_state: "UNAVAILABLE",
    accuracy_limitation: "Location review unavailable. Navigation only; not verified GIS evidence.",
    verification_note: "Pending evidence; geometry presence does not establish verification.",
  };
}
export function mapGeometry(asset: Asset) {
  const location = assetLocation(asset);
  return location.location_status === "NO_LOCATION" ? null : location.geometry;
}
export function locationLayer(asset: Asset) {
  if (asset.asset_code.startsWith("DEV-")) return "DEV";
  if (!asset.asset_code.startsWith("RS-")) return "OTHER";
  return assetLocation(asset).location_status === "VERIFIED_GEOMETRY" ? "RS_VERIFIED" : "RS_REFERENCE";
}
export function hierarchy(assets: Asset[], asset: Asset) {
  const ancestors: Asset[] = [];
  const visited = new Set([asset.id]);
  let parent = assets.find(a => a.id === asset.parent_asset_id);
  while (parent && !visited.has(parent.id)) {
    ancestors.unshift(parent);
    visited.add(parent.id);
    parent = assets.find(a => a.id === parent!.parent_asset_id);
  }
  return { ancestors, children: assets.filter(a => a.parent_asset_id === asset.id) };
}
export function matchesSearch(asset: Asset, query: string, type: string) {
  const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
  return (!type || asset.category.code === type) && normalize(`${asset.id} ${asset.asset_code} ${asset.name} ${asset.category.name}`).includes(normalize(query.trim()));
}

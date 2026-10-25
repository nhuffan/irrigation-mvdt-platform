import { assetDisplayName } from "./asset-display.ts";
import type { Asset, AssetLocation, SpatialDisposition } from "../types/asset";

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
  if (!["REFERENCE_LOCATION", "VERIFIED_GEOMETRY"].includes(location.location_status)) return null;
  return location.geometry;
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
  return (!type || asset.category.code === type) && normalize(`${asset.id} ${asset.asset_code} ${asset.name} ${assetDisplayName(asset)} ${asset.category.name}`).includes(normalize(query.trim()));
}

/** Review disposition is separate from accepted geometry; candidates never become pins. */
export function spatialDisposition(asset: Asset): SpatialDisposition {
  const location = assetLocation(asset);
  if (location.location_status === "REFERENCE_LOCATION" || location.location_status === "VERIFIED_GEOMETRY") return location.location_status;
  return location.spatial_disposition === "CANDIDATE_NEEDS_REVIEW" || location.spatial_disposition === "CONFLICTED"
    ? location.spatial_disposition : "NO_DEFENSIBLE_LOCATION";
}
export function locationMatches(asset: Asset, filter: string) {
  if (filter === "all") return true;
  if (filter === "UNRESOLVED") return ["CANDIDATE_NEEDS_REVIEW", "CONFLICTED"].includes(spatialDisposition(asset));
  if (filter === "NO_LOCATION") return assetLocation(asset).location_status === "NO_LOCATION";
  if (filter === "NO_DEFENSIBLE_LOCATION") return spatialDisposition(asset) === filter;
  return spatialDisposition(asset) === filter;
}
export function spatialCoverage(assets: Asset[]) {
  const unavailable = assets.filter(asset => {
    const location = asset.location;
    return !location || location.review_state === "UNAVAILABLE" ||
      !["NO_LOCATION", "REFERENCE_LOCATION", "VERIFIED_GEOMETRY"].includes(location.location_status) ||
      (location.location_status !== "NO_LOCATION" && (location.review_state !== "AVAILABLE" || !location.geometry));
  }).length;
  const reference = assets.filter(asset => spatialDisposition(asset) === "REFERENCE_LOCATION").length;
  const verified = assets.filter(asset => spatialDisposition(asset) === "VERIFIED_GEOMETRY").length;
  const unresolved = assets.filter(asset => ["CANDIDATE_NEEDS_REVIEW", "CONFLICTED"].includes(spatialDisposition(asset))).length;
  const missing = assets.length - reference - verified - unresolved;
  return { reference, verified, unresolved, missing, unavailable, total: assets.length };
}
/** Identical accepted point coordinates share one marker; positions are never displaced. */
export function pointGroups(assets: Asset[]): Asset[][] {
  const groups = new Map<string, Asset[]>();
  for (const asset of assets) {
    const geometry = mapGeometry(asset);
    if (geometry?.type !== "Point") continue;
    const key = geometry.coordinates.join(",");
    groups.set(key, [...(groups.get(key) ?? []), asset]);
  }
  return [...groups.values()];
}
/** Disambiguate nearby points at the actual zoom without jittering source coordinates. */
export function pointNeighbors(assets: Asset[], selectedId: string, project: (point: [number, number]) => {x:number;y:number}, hitSize = 56): Asset[] {
  const selected = assets.find(asset => asset.id === selectedId);
  const geometry = selected && mapGeometry(selected);
  if (geometry?.type !== "Point") return selected ? [selected] : [];
  const origin = project(geometry.coordinates);
  return assets.filter(asset => {
    const point = mapGeometry(asset);
    if (point?.type !== "Point") return false;
    const screen = project(point.coordinates);
    return Math.abs(screen.x - origin.x) <= hitSize && Math.abs(screen.y - origin.y) <= hitSize;
  });
}

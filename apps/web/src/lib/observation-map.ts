import type { Asset } from "../types/asset";
export const OPERATOR_MAP_URL = "https://thuyloimiennam.vn/vi/gioi-thieu/ban-do-he-thong-thuy-loi-dau-tieng---phuoc-hoa";
export const OBSERVATION_LAYERS = [
  { id: "landsat", name: "Landsat / WELD annual composite", date: "2000-12-01", maxzoom: 12,
    resolution: "30 m nominal · historical annual composite; acquisition dates vary by pixel",
    tiles: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual/default/2000-12-01/GoogleMapsCompatible_Level12/{z}/{y}/{x}.jpeg" },
  { id: "modis", name: "Terra / MODIS true color", date: "2024-02-20", maxzoom: 9,
    resolution: "250 m nominal · daily imagery; clouds, haze and gaps may be present",
    tiles: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-02-20/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpeg" },
] as const;
export function observationReferences(assets: Asset[]) {
  return assets.filter(asset => {
    const location = asset.location;
    if (location?.location_status !== "REFERENCE_LOCATION" || location.review_state !== "AVAILABLE" ||
      !location.reviewed_at || !location.evidence_id || location.crs !== "EPSG:4326" || location.geometry?.type !== "Point") return false;
    const [lon, lat] = location.geometry.coordinates;
    return Number.isFinite(lon) && Number.isFinite(lat) && Math.abs(lon) <= 180 && Math.abs(lat) <= 85.051129;
  });
}

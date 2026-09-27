export type Position = [number, number];
export type GeoJsonGeometry =
  | { type: "Point"; coordinates: Position }
  | { type: "LineString"; coordinates: Position[] }
  | { type: "Polygon"; coordinates: Position[][] };
export type AssetCategory = { id: string; code: string; name: string };
export type Asset = {
  id: string;
  reservoir_id: string;
  parent_asset_id: string | null;
  asset_code: string;
  name: string;
  description: string | null;
  technical_description: string | null;
  condition_status: string | null;
  data_status: "REGISTERED" | "PARTIAL" | "VERIFIED";
  category: AssetCategory;
  geometry: GeoJsonGeometry | null;
};

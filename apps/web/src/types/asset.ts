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
  location?: AssetLocation | null;
};

export type AssetLocation = {
  location_status: "VERIFIED_GEOMETRY" | "REFERENCE_LOCATION" | "NO_LOCATION";
  geometry: GeoJsonGeometry | null;
  geometry_type: GeoJsonGeometry["type"] | null;
  crs: string | null;
  source: string | null;
  source_url?: string | null;
  locator: string | null;
  evidence_id: string | null;
  accuracy_limitation: string;
  verification_note: string;
  reviewer: string | null;
  reviewed_at: string | null;
  review_state: "AVAILABLE" | "PENDING" | "UNAVAILABLE";
};

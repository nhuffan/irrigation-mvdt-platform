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

export type SpatialDisposition = "VERIFIED_GEOMETRY" | "REFERENCE_LOCATION" | "CANDIDATE_NEEDS_REVIEW" | "CONFLICTED" | "NO_DEFENSIBLE_LOCATION";
export type SpatialCandidate = {
  candidate_id: string;
  source_label: string;
  source: string;
  source_url?: string | null;
  document_id?: string | null;
  physical_page?: number | null;
  locator: string;
  coordinate_basis: string;
  source_crs: string;
  identity_basis: string;
  accuracy_limitation: string;
  issues: string[];
};
export type AssetLocation = {
  spatial_disposition?: SpatialDisposition;
  candidate_count?: number;
  reason?: string | null;
  next_action?: string | null;
  candidates?: SpatialCandidate[];
  coordinate_basis?: string | null;
  estimated_accuracy_m?: number | null;
  physical_page?: number | null;
  document_id?: string | null;
  source_id?: string | null;
  source_sha256?: string | null;
  reviewer_role?: string | null;
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

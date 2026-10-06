import type { DataSource, VerificationStatus } from "./data-source";
export interface DocumentRecord {
  id: string;
  source_id: string;
  document_code: string;
  original_file_name: string;
  mime_type: string | null;
  file_size: number | null;
  checksum_sha256: string | null;
  page_count: number | null;
  uploaded_at: string;
  source: DataSource;
}
export interface ModelRecord {
  id: string;
  reservoir_id: string;
  source_id: string | null;
  model_code: string;
  name: string;
  model_type: string;
  format: string;
  coordinate_mode: string;
  longitude: number | null;
  latitude: number | null;
  height: number | null;
  heading: number;
  pitch: number;
  roll: number;
  scale: number;
  verification_status: VerificationStatus;
  source: DataSource | null;
}
export interface ModelAssetLink {
  id: string;
  model_id: string;
  asset_id: string;
  reservoir_id: string;
  object_key: string;
  object_name: string | null;
  verification_status: VerificationStatus;
}

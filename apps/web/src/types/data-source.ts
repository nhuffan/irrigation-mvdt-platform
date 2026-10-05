export type VerificationStatus =
  | "UNVERIFIED"
  | "PARTIALLY_VERIFIED"
  | "VERIFIED"
  | "REJECTED";
export type DataSource = {
  id: string;
  reservoir_id: string;
  source_code: string;
  source_type: string;
  title: string;
  file_name: string | null;
  source_date: string | null;
  source_owner: string | null;
  authority_level: string | null;
  verification_status: VerificationStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
};
export type SourcedRecord = {
  id: string;
  asset_id: string;
  source_id: string | null;
  source: DataSource | null;
  verification_status: VerificationStatus;
  created_at: string;
  updated_at: string;
};

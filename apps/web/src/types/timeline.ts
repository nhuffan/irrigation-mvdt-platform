import type { DataSource, VerificationStatus } from "./data-source";
export type TimelineEvent = {
  event_type: "CONDITION" | "INSPECTION" | "REPAIR" | "MAINTENANCE";
  event_date: string;
  title: string;
  summary: string | null;
  record_id: string;
  asset_id: string;
  source_id: string | null;
  source: DataSource | null;
  verification_status: VerificationStatus;
};

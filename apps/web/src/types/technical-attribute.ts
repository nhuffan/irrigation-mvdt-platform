import type { SourcedRecord } from "./data-source";
export type TechnicalAttribute = SourcedRecord & {
  attribute_key: string;
  attribute_label: string;
  value_text: string | null;
  value_number: number | null;
  unit: string | null;
  reviewed_provenance: {
    verification_level: string; source_code: string; evidence_id: string;
    source_locator: string; authority: string; reviewer: string; reviewed_at: string;
  } | null;
};

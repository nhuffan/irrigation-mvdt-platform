import type { SourcedRecord } from "./data-source";
export type Inspection = SourcedRecord & {
  inspection_date: string;
  inspection_type: string | null;
  inspector: string | null;
  summary: string | null;
  observation: string | null;
  condition_status: string | null;
  recommended_action: string | null;
};

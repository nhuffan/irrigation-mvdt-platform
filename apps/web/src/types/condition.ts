import type { SourcedRecord } from "./data-source";
export type Condition = SourcedRecord & {
  condition_date: string;
  condition_status: string;
  summary: string | null;
  defect_description: string | null;
  recommended_action: string | null;
};

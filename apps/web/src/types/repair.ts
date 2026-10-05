import type { SourcedRecord } from "./data-source";
export type Repair = SourcedRecord & {
  repair_date: string;
  repair_type: string | null;
  problem_description: string | null;
  repair_description: string;
  result: string | null;
  responsible_unit: string | null;
};

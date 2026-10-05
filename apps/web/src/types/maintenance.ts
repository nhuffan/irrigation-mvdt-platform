import type { SourcedRecord } from "./data-source";
export type Maintenance = SourcedRecord & {
  maintenance_date: string;
  maintenance_type: string | null;
  description: string;
  result: string | null;
  responsible_unit: string | null;
};

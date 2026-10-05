import type { SourcedRecord } from "./data-source";
export type TechnicalAttribute = SourcedRecord & {
  attribute_key: string;
  attribute_label: string;
  value_text: string | null;
  value_number: number | null;
  unit: string | null;
};

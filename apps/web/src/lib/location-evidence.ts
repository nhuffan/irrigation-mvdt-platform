import type { Asset } from "../types/asset";
import { assetLocation } from "./asset-location.ts";
import { evidenceDisplayText } from "./evidence-display.ts";
import { publicEvidenceHref, publicEvidenceText } from "./asset-information.ts";

/** Shared popup evidence fields; no private receipt or reviewer identity is published. */
export function locationEvidence(asset: Asset) {
  const l = assetLocation(asset);
  const text = (value: string | null | undefined) => value ? publicEvidenceText(value) : "Unknown";
  const fields: [string, string][] = [
    ["Source", evidenceDisplayText(text(l.source))], ["Locator", text(l.locator)],
    ["Coordinate basis", text(l.coordinate_basis)],
    ["Review", l.review_state === "AVAILABLE" ? `Accepted${l.reviewer_role ? ` · ${l.reviewer_role}` : ""}${l.reviewed_at ? ` · ${l.reviewed_at}` : ""}` : l.review_state],
    ["Estimated accuracy", l.estimated_accuracy_m == null ? "Unknown" : `${l.estimated_accuracy_m} m`],
    ["Limitation", text(l.accuracy_limitation)],
  ];
  if (l.candidate_count && l.reason) fields.push(["Source comparison", text(l.reason)]);
  return {fields, ...locationSource(l)};
}

/** Validate page and document identity without guessing them from a locator. */
export function locationSource(value: {document_id?:string|null; physical_page?:number|null; source_url?:string|null}) {
  const documentId = value.document_id && /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(value.document_id) ? value.document_id : null;
  const page = Number.isInteger(value.physical_page) && value.physical_page! > 0 ? value.physical_page : null;
  return {href: documentId ? `/documents/${documentId}${page ? `?page=${page}` : ""}` : publicEvidenceHref(value.source_url), page};
}

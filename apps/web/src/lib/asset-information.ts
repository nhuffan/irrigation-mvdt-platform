import type { TechnicalAttribute } from "../types/technical-attribute";
import type { DocumentRecord } from "../types/media";
import { evidenceDisplayText } from "./evidence-display.ts";

const privatePath = /(?:file:\/\/[^\s<>"']*|\/(?:Users|home|private|tmp|var|mnt|Volumes)\/[^\s<>"']*|[A-Za-z]:\\[^\s<>"']*)/gi;
/** Publication display only: canonical evidence and API values are unchanged. */
export function publicEvidenceText(value: string | null | undefined) {
  if (value === null || value === undefined) return "Not available";
  return value.replace(privatePath, "[private path omitted]");
}
/** Public http(s) sources and same-site paths only; never publish local files or keyed links. */
export function publicEvidenceHref(value: string | null | undefined): string | null {
  if (!value || value !== value.trim() || /[\\\s]/.test(value)) return null;
  let decoded: string;
  try { decoded = decodeURIComponent(value); } catch { return null; }
  if (privatePath.test(decoded)) { privatePath.lastIndex = 0; return null; }
  privatePath.lastIndex = 0;
  const internal = value.startsWith("/") && !value.startsWith("//");
  try {
    const url = new URL(value, internal ? "https://publication.invalid" : undefined);
    const host = url.hostname.toLowerCase();
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password ||
      host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local") ||
      /^(?:127\.|10\.|192\.168\.|169\.254\.|0\.)/.test(host) ||
      /^172\.(?:1[6-9]|2\d|3[01])\./.test(host) || host.includes(":")) return null;
    if ([...url.searchParams.keys()].some(key => /^(?:key|token|api_key|access_token|authorization|secret)$/i.test(key))) return null;
    return value;
  } catch { return null; }
}
export function technicalValueDetails(record: Pick<TechnicalAttribute, "value_number" | "value_text" | "unit">) {
  const number = record.value_number;
  const text = record.value_text;
  const hasText = typeof text === "string" && text.trim() !== "";
  const invalidNumber = number !== null && number !== undefined && !Number.isFinite(number);
  const hasNumber = typeof number === "number" && Number.isFinite(number);
  const valueState = hasNumber || hasText ? "AVAILABLE" : invalidNumber ? "INVALID_NUMBER" : text !== null && text !== undefined ? "EMPTY_TEXT" : "MISSING";
  const value = hasNumber ? number : hasText ? evidenceDisplayText(publicEvidenceText(text)) : valueState === "EMPTY_TEXT" ? "Empty text in source record" : valueState === "INVALID_NUMBER" ? "Invalid numeric value" : "Not available";
  const isTextUnit = record.unit?.trim().toLowerCase() === "text";
  const unit = record.unit == null ? "Not reported" : !record.unit.trim() ? "Not reported (empty unit)" : isTextUnit ? "Text value (no physical unit)" : publicEvidenceText(record.unit);
  return { value, valueState, unit, valueUnit: isTextUnit || record.unit == null || !record.unit.trim() ? null : publicEvidenceText(record.unit),
    additionalText: hasNumber && hasText ? evidenceDisplayText(publicEvidenceText(text)) : null };
}
export function linkedDocumentCounts(documents: Pick<DocumentRecord, "id" | "mime_type" | "checksum_sha256">[] | null) {
  if (documents === null) return { edges: null, distinctPdfHashes: null, unhashablePdfs: null };
  const pdfs = documents.filter(d => d.mime_type?.toLowerCase().split(";")[0].trim() === "application/pdf");
  const unknownType = documents.some(d => !d.mime_type?.trim());
  const unhashablePdfs = pdfs.filter(d => !/^[a-f0-9]{64}$/i.test(d.checksum_sha256 ?? "")).length;
  return { edges: documents.length,
    distinctPdfHashes: unhashablePdfs || unknownType ? null : new Set(pdfs.map(d => d.checksum_sha256!.toLowerCase())).size,
    unhashablePdfs };
}

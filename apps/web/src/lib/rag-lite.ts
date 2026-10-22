export type RagCitation = {
  citation_id: string;
  kind: "technical_attribute" | "document_chunk";
  source_id: string;
  source_code: string;
  document_id: string | null;
  record_id: string | null;
  page: number | null;
  locator: string;
  asset_id: string | null;
  url: string;
  content_url: string | null;
  title: string;
  excerpt: string;
  checksum_sha256: string | null;
  attribute_key: string | null;
  value_number: number | null;
  value_text: string | null;
  unit: string | null;
  evidence_id: string | null;
  source_date: string | null;
  record_status: string | null;
  source_status: string;
  authority: string | null;
};

export type RagResult = {
  status: "ANSWERED" | "RETRIEVAL_ONLY" | "NOT_ENOUGH_EVIDENCE" | "GENERATION_UNAVAILABLE";
  answer: string | null;
  asset_id: string | null;
  citations: RagCitation[];
  limitations: string[];
};

export type RagDemo = { question: string; attribute_key: string; attribute_label?: string };

export type RagCoverage = {
  authorized_documents: number;
  searchable_documents: number;
  image_only_documents: number;
  unavailable_documents: number;
  searchable_pages: number;
  indexed_chunks: number;
};

/** Retrieval integrity failures require a different recovery path from a completed search with no match. */
export function criticalRetrievalIssue(result: RagResult): boolean {
  return result.limitations.some(line => {
    // Provider availability is separate from the integrity of retained retrieval evidence.
    if (line === "Generation unavailable or invalid; original retrieval evidence retained") return false;
    return /\b(?:missing|stale|invalid|unauthori[sz]ed|not authori[sz]ed|integrity|checksum|mismatch|revoked)\b/i.test(line);
  });
}

export function resultHeading(result: RagResult): string {
  if (result.status !== "ANSWERED" && criticalRetrievalIssue(result)) {
    return result.citations.length ? "Supporting evidence found · search incomplete" : "Evidence retrieval unavailable";
  }
  switch (result.status) {
    case "ANSWERED": return "Evidence-backed answer";
    case "RETRIEVAL_ONLY": return "Supporting evidence found";
    case "GENERATION_UNAVAILABLE":
      return result.citations.length ? "Evidence found · AI summary unavailable" : "No supporting evidence found";
    case "NOT_ENOUGH_EVIDENCE": return "No supporting evidence found";
  }
}

/** Keep source values canonical; translation belongs only to descriptive labels. */
export function displayValue(citation: RagCitation): string {
  const value = typeof citation.value_number === "number" && Number.isFinite(citation.value_number)
    ? citation.value_number : citation.value_text;
  if (value === null || value === undefined) return "Unknown";
  const unit = citation.unit;
  return `${value}${unit?.trim() && unit.trim().toLowerCase() !== "text" ? ` ${unit}` : ""}`;
}

/** Group only passages, retaining every returned entry and its original within-document order. */
export function groupDocuments(citations: RagCitation[]): { documentId: string; citations: RagCitation[] }[] {
  const groups = new Map<string, RagCitation[]>();
  for (const citation of citations) {
    if (citation.kind !== "document_chunk") continue;
    // Even malformed metadata remains inspectable; it must not silently drop evidence.
    const key = citation.document_id ?? `unresolved:${citation.citation_id}`;
    const entries = groups.get(key);
    if (entries) entries.push(citation);
    else groups.set(key, [citation]);
  }
  return [...groups].map(([documentId, entries]) => ({ documentId, citations: entries }));
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function isUuid(value: string | null): value is string { return typeof value === "string" && uuid.test(value); }

/** Generate only known same-site routes, after checking that supplied evidence metadata agrees. */
export function citationHref(citation: RagCitation, kind: "evidence" | "original" | "source" | "download"): string | null {
  if (!isUuid(citation.source_id) || (citation.asset_id !== null && !isUuid(citation.asset_id))) return null;
  let evidence: string;
  if (citation.kind === "technical_attribute") {
    if (!isUuid(citation.asset_id) || !isUuid(citation.record_id) || citation.document_id !== null) return null;
    evidence = `/assets/${citation.asset_id}`;
  } else if (citation.kind === "document_chunk" && isUuid(citation.document_id)) {
    evidence = `/documents/${citation.document_id}`;
  } else return null;
  if (citation.url !== evidence) return null;
  if (kind === "evidence") return citation.kind === "technical_attribute" ? `${evidence}#record-${citation.record_id}` : evidence;
  if (kind === "source") return `/data-sources/${citation.source_id}/documents`;
  if (citation.kind !== "document_chunk" || !Number.isSafeInteger(citation.page) || citation.page! < 1) return null;
  const original = `/api/media/documents/${citation.document_id}`;
  if (citation.content_url !== `${original}#page=${citation.page}`) return null;
  return kind === "original" ? `${original}#page=${citation.page}` : `${original}?download=true`;
}

export function needsOpenLimitations(result: RagResult): boolean {
  if (!result.citations.length || result.status === "NOT_ENOUGH_EVIDENCE") return true;
  return criticalRetrievalIssue(result);
}

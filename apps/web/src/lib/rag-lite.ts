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
  reason_codes?: string[];
  pagination?: { page: number; page_size: number; total_results: number; total_pages: number } | null;
};

export type RagDemo = { question: string; attribute_key: string | null; attribute_label?: string; query_type?: "document" };

export type RagCoverage = {
  authorized_documents: number;
  searchable_documents: number;
  image_only_documents: number;
  unavailable_documents: number;
  searchable_pages: number;
  indexed_chunks: number;
  diagnostics?: {
    asset_id: string;
    reviewed_attributes: number;
    direct_documents: number;
    not_authorized_documents: number;
    missing_documents: number;
    invalid_documents: number;
    invalid_indexes: number;
    extraction_limited_documents: number;
    unscoped_documents?: number;
    unknown_metadata_sources: number;
    reason_codes: string[];
  };
};

/** Retrieval integrity failures require a different recovery path from a completed search with no match. */
export function criticalRetrievalIssue(result: RagResult): boolean {
  if (result.reason_codes?.some(code => ["INDEX_INVALID", "DOCUMENT_MISSING", "DOCUMENT_INVALID"].includes(code))) return true;
  return result.limitations.some(line => {
    // Provider availability is separate from the integrity of retained retrieval evidence.
    if (line === "Generation unavailable or invalid; original retrieval evidence retained") return false;
    return /\b(?:missing|stale|invalid|unauthori[sz]ed|not authori[sz]ed|integrity|checksum|mismatch|revoked)\b/i.test(line);
  });
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

/** Codes come from live, scope-bound checks; never infer absent sources from no hits. */
export function evidenceReasonText(code: string): string | null {
  const messages: Record<string, string> = {
    NO_DIRECT_DOCUMENT: "No PDF is directly linked through reviewed evidence in this scope. Technical records may still be available.",
    NO_REVIEWED_ATTRIBUTE: "No reviewed technical attribute is available for this asset. Parent and component evidence stays separate.",
    NOT_AUTHORIZED: "Some linked PDFs are not authorized for local search. They have not been searched.",
    IMAGE_ONLY: "Some authorized PDFs have no extracted text (image-only coverage). Text search cannot read them; no OCR is used.",
    INDEX_INVALID: "The local index is absent, stale or invalid. Verify it against the authorized original before retrying.",
    DOCUMENT_MISSING: "An authorized original PDF is missing from local storage. Its indexed text cannot be used.",
    DOCUMENT_INVALID: "An authorized original could not pass its checksum or file checks. Its indexed text cannot be used.",
    EXTRACTION_LIMITED: "Search covers only indexed passages. Some pages were excluded or have limited extracted text; inspect the original.",
    NO_SCOPED_PASSAGE: "The linked PDF has no reviewed passage for this exact asset. Its other sections stay separate; reviewed fields may still be available.",
    NO_MATCH: "No passage or reviewed field matched these keywords. Try wording from the original; missing hits do not prove evidence is absent.",
    SOURCE_METADATA_UNKNOWN: "Some source dates or authorities are not recorded. Unknown metadata is not independent source verification.",
    OUT_OF_SCOPE: "This request asks beyond historical evidence retrieval or to bypass evidence rules. Current condition and operational advice are outside scope.",
    SCOPE_MISMATCH: "The asset is outside this reservoir or the question names another asset. Select the exact asset or component.",
  };
  return messages[code] ?? null;
}

export function metadataLabel(value: string | null | undefined): string {
  return !value?.trim() || value === "UNKNOWN" ? "Unknown" : value;
}


/** One outcome per search; full diagnostics remain available on demand. */
export function searchFeedback(result: RagResult): { title: string; description: string } {
  const count = result.pagination?.total_results ?? result.citations.length;
  if (criticalRetrievalIssue(result)) return {
    title: count ? `${count} ${count === 1 ? "reference" : "references"} · incomplete` : "Documents unavailable",
    description: count ? "Some documents could not be searched. Available references are shown below." : "Verify the original files and local index, then retry.",
  };
  if (count) return {
    title: `${count} ${count === 1 ? "reference" : "references"}`,
    description: result.status === "GENERATION_UNAVAILABLE" ? "AI summary unavailable; original evidence is shown below." : "",
  };
  const codes = result.reason_codes ?? [];
  if (codes.includes("OUT_OF_SCOPE")) return { title: "Outside search scope", description: "Search covers historical evidence, not current condition or operating advice." };
  if (codes.includes("SCOPE_MISMATCH")) return { title: "Check the selected asset", description: "Select the exact asset or component named in your question." };
  if (codes.includes("NO_DIRECT_DOCUMENT") && codes.includes("NO_REVIEWED_ATTRIBUTE")) return { title: "No linked evidence", description: "This asset has no reviewed fields or directly linked PDFs." };
  if (codes.includes("NO_DIRECT_DOCUMENT")) return { title: "No matching evidence", description: "No directly linked PDF is available for this asset. Try a reviewed field or search all authorized PDFs." };
  if (codes.includes("NOT_AUTHORIZED") && !codes.includes("NO_MATCH")) return { title: "Search access limited", description: "Linked PDFs are not authorized for local search." };
  if (codes.includes("IMAGE_ONLY") && !codes.includes("NO_MATCH")) return { title: "No searchable text", description: "The linked PDFs are image-only. Text search cannot read them." };
  if (codes.includes("EXTRACTION_LIMITED") && !codes.includes("NO_MATCH")) return { title: "No searchable match", description: "The linked originals have limited extracted text." };
  if (codes.includes("NO_SCOPED_PASSAGE") && !codes.includes("NO_MATCH")) return { title: "No reviewed PDF passages", description: "The linked original has no reviewed passage for this exact asset. Try a reviewed field or search all authorized PDFs." };
  if (codes.includes("NO_REVIEWED_ATTRIBUTE")) return { title: "No reviewed fields", description: "No reviewed technical fields are available for this asset." };
  return { title: "No matches", description: "Try fewer keywords or wording from the original document." };
}


/** Keep first/last and nearby page numbers, without a long row on small screens. */
export function paginationItems(page: number, total: number): (number | "…")[] {
  if (total < 1) return [];
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const nearby = page <= 3 ? [1, 2, 3, 4, 5] : page >= total - 2
    ? [total - 4, total - 3, total - 2, total - 1, total] : [page - 1, page, page + 1];
  const visible = [...new Set([1, total, ...nearby])].filter(n => n >= 1 && n <= total).sort((a, b) => a - b);
  const items: (number | "…")[] = [];
  for (const n of visible) {
    const previous = items.at(-1);
    if (typeof previous === "number") {
      if (n - previous === 2) items.push(previous + 1);
      else if (n - previous > 2) items.push("…");
    }
    items.push(n);
  }
  return items;
}

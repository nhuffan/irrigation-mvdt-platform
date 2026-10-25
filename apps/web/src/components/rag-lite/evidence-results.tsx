"use client";

import type { RefObject } from "react";
import { OriginLink } from "@/components/documents/document-link";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { citationHref, criticalRetrievalIssue, displayValue, evidenceReasonText, metadataLabel, groupDocuments, searchFeedback, paginationItems, type RagCitation, type RagResult } from "@/lib/rag-lite";
import styles from "./rag-lite.module.css";

function EvidenceDetails({ citation: c }: { citation: RagCitation }) {
  const fields = [
    ["Source", `${c.source_code} · ${c.source_id}`], ["Asset ID", c.asset_id ?? "Corpus-wide; no asset attribution"],
    ["Record ID", c.record_id], ["Attribute key", c.attribute_key], ["Evidence ID", c.evidence_id],
    ["Original locator", c.locator], ["Source date", c.source_date ?? "Unknown"],
    ["Record status", c.record_status], ["Source status", metadataLabel(c.source_status)], ["Source authority", metadataLabel(c.authority)],
    ["Original SHA-256", c.checksum_sha256], ["Citation ID", c.citation_id],
  ];
  return <details className={styles.details}>
    <summary>Evidence details</summary>
    <dl className={styles.metadata}>{fields.filter(([, value]) => value !== null).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    <div className={styles.detailActions}>
      <EvidenceLink citation={c} kind="source">Source details</EvidenceLink>
      {c.kind === "document_chunk" && <><EvidenceLink citation={c} kind="evidence">Document details</EvidenceLink><EvidenceLink citation={c} kind="download">Download PDF</EvidenceLink></>}
    </div>
  </details>;
}

function EvidenceLink({ citation, kind, children, primary = false }: {
  citation: RagCitation; kind: "evidence" | "original" | "source" | "download"; children: React.ReactNode; primary?: boolean;
}) {
  const href = citationHref(citation, kind);
  if (href && (kind === "evidence" || kind === "source")) {
    const target = kind === "evidence" && citation.kind === "document_chunk" ? `${href}?page=${citation.page ?? 1}` : href;
    return <OriginLink className={primary ? styles.primaryLink : "text-link"} href={target} returnAnchor={citation.citation_id}>{children}</OriginLink>;
  }
  return href ? <a className={primary ? styles.primaryLink : "text-link"} href={href}>{children}</a> : null;
}

function AttributeCard({ citation: c }: { citation: RagCitation }) {
  return <article id={c.citation_id} tabIndex={-1} className={`panel ${styles.attributeCard}`}>
    <div className={styles.tags}><span>{c.source_code}</span>{c.record_status && <span>Record: {c.record_status}</span>}<span>Source: {metadataLabel(c.source_status)}</span></div>
    <h3>{evidenceDisplayText(c.title)}</h3>
    <p className={styles.value}>{(c.value_number === null && c.value_text !== null && c.value_text !== ""
      ? evidenceDisplayText(displayValue(c)) : displayValue(c)) || <span className={styles.muted}>Empty text recorded</span>}</p>
    <div className={styles.actions}>
      <EvidenceLink citation={c} kind="evidence" primary>View asset evidence <span aria-hidden="true">↗</span></EvidenceLink>
    </div>
    <EvidenceDetails citation={c} />
  </article>;
}

function Passage({ citation: c }: { citation: RagCitation }) {
  const original = citationHref(c, "original");
  return <section id={c.citation_id} tabIndex={-1} className={styles.passage} aria-label={`Physical PDF page ${c.page ?? "unknown"}`}>
    <p className={styles.pageLabel}>Physical PDF page {c.page ?? "Unknown"}</p>
    <div className={styles.excerpt}><p className={styles.clamp}>{c.excerpt}</p><details>
      <summary><span className={styles.expandText}>Expand excerpt</span><span className={styles.collapseText}>Collapse excerpt</span></summary>
      <p className={styles.fullExcerpt}>{c.excerpt}</p>
    </details></div>
    <div className={styles.actions}>
      {original ? <EvidenceLink citation={c} kind="original" primary>Open original PDF (page {c.page}) <span aria-hidden="true">↗</span></EvidenceLink> : <EvidenceLink citation={c} kind="evidence" primary>Open document</EvidenceLink>}
    </div>
    <EvidenceDetails citation={c} />
  </section>;
}

function DocumentCard({ citations }: { citations: RagCitation[] }) {
  const first = citations[0];
  return <article className={`panel ${styles.documentCard}`}>
    <header className={styles.documentHeading}>
      <div className={styles.tags}><span>{first.source_code}</span><span>Source: {metadataLabel(first.source_status)}</span></div>
      <h3>{evidenceDisplayText(first.title)}</h3>
    </header>
    {citations.map(c => <Passage key={c.citation_id} citation={c} />)}
  </article>;
}

function revealCitation(id: string) {
  const target = document.getElementById(id);
  for (let parent = target?.parentElement; parent; parent = parent.parentElement) {
    if (parent instanceof HTMLDetailsElement) parent.open = true;
  }
  target?.scrollIntoView({ block: "center", behavior: "smooth" });
  target?.focus({ preventScroll: true });
}

export function EvidenceResults({ result, headingRef, onCorpus, onPage }: {
  result: RagResult; headingRef: RefObject<HTMLHeadingElement | null>; onCorpus?: () => void; onPage: (page: number) => void;
}) {
  const attributes = result.citations.filter(c => c.kind === "technical_attribute");
  const documents = groupDocuments(result.citations);
  const retrievalIssue = criticalRetrievalIssue(result);
  const feedback = searchFeedback(result);
  const paging = result.pagination;
  const reasonText = result.reason_codes?.map(evidenceReasonText).filter(Boolean).join(" ");
  return <section className={styles.results} aria-label="Search results" aria-describedby={reasonText ? "search-reason-details" : undefined}>
    {reasonText && <p id="search-reason-details" className={styles.srOnly}>{reasonText}</p>}
    <header className={styles.resultHeading}>
      <h2 ref={headingRef} tabIndex={-1}>{feedback.title}</h2>
      {feedback.description && <p>{feedback.description}</p>}
      {!result.citations.length && onCorpus && !retrievalIssue && !result.reason_codes?.some(code => ["OUT_OF_SCOPE", "SCOPE_MISMATCH"].includes(code)) && <div className={styles.emptyActions}>
        <button type="button" className="text-link" onClick={onCorpus}>Search all authorized PDFs</button>
        <span>Corpus-wide; no asset attribution.</span>
      </div>}
    </header>
    {result.status === "ANSWERED" && result.answer && <div className={`panel ${styles.answer}`}>
      {result.answer.split(/(\[[^\]]+\])/g).map((part, i) => {
        const c = result.citations.find(citation => part === `[${citation.citation_id}]`);
        return c ? <a className="text-link" key={i} href={`#${c.citation_id}`} onClick={() => revealCitation(c.citation_id)}>[{result.citations.indexOf(c) + 1}]</a> : part;
      })}
    </div>}
    {attributes.length > 0 && <div className={styles.attributeGrid}>{attributes.map(c => <AttributeCard key={c.citation_id} citation={c} />)}</div>}
    {documents.map(group => <DocumentCard key={group.documentId} citations={group.citations} />)}
    {paging && paging.total_pages > 1 && <nav className={styles.pagination} aria-label="Search result pages">
      <span className={styles.pageRange}>{(paging.page - 1) * paging.page_size + 1}–{Math.min(paging.page * paging.page_size, paging.total_results)} of {paging.total_results}</span>
      <div className={styles.pageButtons}>
        <button type="button" disabled={paging.page === 1} onClick={() => onPage(paging.page - 1)} aria-label="Previous page">‹</button>
        {paginationItems(paging.page, paging.total_pages).map((item, i) => item === "…"
          ? <span key={`gap-${i}`} aria-hidden="true">…</span>
          : <button type="button" key={item} aria-label={`Page ${item}`} aria-current={item === paging.page ? "page" : undefined} onClick={() => { if (item !== paging.page) onPage(item); }}>{item}</button>)}
        <button type="button" disabled={paging.page === paging.total_pages} onClick={() => onPage(paging.page + 1)} aria-label="Next page">›</button>
      </div>
    </nav>}

  </section>;
}

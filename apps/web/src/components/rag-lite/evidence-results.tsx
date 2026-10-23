"use client";

import type { RefObject } from "react";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { citationHref, criticalRetrievalIssue, displayValue, evidenceReasonText, metadataLabel, groupDocuments, needsOpenLimitations, resultHeading, type RagCitation, type RagResult } from "@/lib/rag-lite";
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
  </details>;
}

function EvidenceLink({ citation, kind, children, primary = false }: {
  citation: RagCitation; kind: "evidence" | "original" | "source" | "download"; children: React.ReactNode; primary?: boolean;
}) {
  const href = citationHref(citation, kind);
  return href ? <a className={primary ? styles.primaryLink : "text-link"} href={href}>{children}</a> : null;
}

function SourceSummary({ citation: c }: { citation: RagCitation }) {
  return <p className={styles.provenance}>Source {c.source_code} · Status: {metadataLabel(c.source_status)} · Authority: {metadataLabel(c.authority)} · Date: {metadataLabel(c.source_date)}</p>;
}

function AttributeCard({ citation: c }: { citation: RagCitation }) {
  return <article id={c.citation_id} tabIndex={-1} className={`panel ${styles.attributeCard}`}>
    <div className={styles.tags}><span>Historical / Reference</span><span>{c.source_code}</span>{c.record_status && <span>Record: {c.record_status}</span>}</div>
    <h3>{evidenceDisplayText(c.title)}</h3>
    <SourceSummary citation={c} />
    <p className={styles.value}>{(c.value_number === null && c.value_text !== null && c.value_text !== ""
      ? evidenceDisplayText(displayValue(c)) : displayValue(c)) || <span className={styles.muted}>Empty text recorded</span>}</p>
    <div className={styles.actions}>
      <EvidenceLink citation={c} kind="evidence" primary>View asset evidence <span aria-hidden="true">↗</span></EvidenceLink>
      <EvidenceLink citation={c} kind="source">Source details</EvidenceLink>
    </div>
    <EvidenceDetails citation={c} />
  </article>;
}

function Passage({ citation: c }: { citation: RagCitation }) {
  const original = citationHref(c, "original");
  return <section id={c.citation_id} tabIndex={-1} className={styles.passage} aria-label={`Physical PDF page ${c.page ?? "unknown"}`}>
    <p className={styles.pageLabel}>Physical PDF page {c.page ?? "Unknown"}</p>
    <SourceSummary citation={c} />
    <div className={styles.excerpt}><p className={styles.clamp}>{c.excerpt}</p><details>
      <summary><span className={styles.expandText}>Expand excerpt</span><span className={styles.collapseText}>Collapse excerpt</span></summary>
      <p className={styles.fullExcerpt}>{c.excerpt}</p>
    </details></div>
    <div className={styles.actions}>
      {original ? <EvidenceLink citation={c} kind="original" primary>Open original PDF (page {c.page}) <span aria-hidden="true">↗</span></EvidenceLink> : <EvidenceLink citation={c} kind="evidence" primary>Open document</EvidenceLink>}
      {original && <EvidenceLink citation={c} kind="evidence">Document details</EvidenceLink>}
      <EvidenceLink citation={c} kind="download">Download</EvidenceLink>
      <EvidenceLink citation={c} kind="source">Source details</EvidenceLink>
    </div>
    <EvidenceDetails citation={c} />
  </section>;
}

function DocumentCard({ citations }: { citations: RagCitation[] }) {
  const first = citations[0];
  return <article className={`panel ${styles.documentCard}`}>
    <header className={styles.documentHeading}>
      <div className={styles.tags}><span>Original document</span><span>{first.source_code}</span><span>{citations.length} {citations.length === 1 ? "passage" : "passages"}</span></div>
      <h3>{evidenceDisplayText(first.title)}</h3>
    </header>
    <Passage citation={first} />
    {citations.length > 1 && <details className={styles.morePassages}>
      <summary>{citations.length - 1} more {citations.length === 2 ? "passage" : "passages"} from this document</summary>
      {citations.slice(1).map(c => <Passage key={c.citation_id} citation={c} />)}
    </details>}
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

export function EvidenceResults({ result, scopeName, query, headingRef }: {
  result: RagResult; scopeName: string; query: string; headingRef: RefObject<HTMLHeadingElement | null>;
}) {
  const attributes = result.citations.filter(c => c.kind === "technical_attribute");
  const documents = groupDocuments(result.citations);
  const retrievalIssue = criticalRetrievalIssue(result);
  return <section className={styles.results} aria-label="Search results">
    <header className={styles.resultHeading}>
      <div><p className="eyebrow">Search results for {scopeName}</p><h2 ref={headingRef} tabIndex={-1}>{resultHeading(result)}</h2><p className={styles.query}>“{query}”</p></div>
      {result.citations.length > 0 && <span className={styles.count}>{result.citations.length} {result.citations.length === 1 ? "reference" : "references"}</span>}
    </header>
    {retrievalIssue && result.citations.length > 0 && <div className={`panel ${styles.error}`} role="note">
      <h3>Search incomplete</h3>
      <p>Some authorized evidence could not be verified or searched. Verify the original PDFs, checksums, and local index, then retry. The returned references remain available for review.</p>
    </div>}
    {result.status === "ANSWERED" && result.answer && <div className={`panel ${styles.answer}`}>
      {result.answer.split(/(\[[^\]]+\])/g).map((part, i) => {
        const c = result.citations.find(citation => part === `[${citation.citation_id}]`);
        return c ? <a className="text-link" key={i} href={`#${c.citation_id}`} onClick={() => revealCitation(c.citation_id)}>[{result.citations.indexOf(c) + 1}]</a> : part;
      })}
    </div>}
    {!result.citations.length && <div className={`panel ${styles.empty}`}>
      <h3>{retrievalIssue ? "The authorized document search could not be completed." : "No evidence supports this request in the selected scope."}</h3>
      <p>{retrievalIssue ? "Verify the original PDFs, their checksums, and the local search index, then retry. No conclusion about the availability of supporting evidence can be drawn from this failed search." : "Choose the exact asset or component and try keywords used in the original document. You can explicitly select all authorized PDFs to broaden the search."}</p>
      {!!result.reason_codes?.length && <ul className={styles.reasons}>{result.reason_codes.map(evidenceReasonText).filter(Boolean).map(message => <li key={message}>{message}</li>)}</ul>}
    </div>}
    {attributes.length > 0 && <div className={styles.attributeGrid}>{attributes.map(c => <AttributeCard key={c.citation_id} citation={c} />)}</div>}
    {documents.map(group => <DocumentCard key={group.documentId} citations={group.citations} />)}
    <details className={`panel ${styles.limitations}`} open={needsOpenLimitations(result)}>
      <summary>Scope &amp; limitations</summary>
      <ul>{result.limitations.map((line, i) => <li key={i}>{line}</li>)}</ul>
    </details>
  </section>;
}

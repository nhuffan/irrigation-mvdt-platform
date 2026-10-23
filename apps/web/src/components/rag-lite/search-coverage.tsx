import { evidenceReasonText, type RagCoverage } from "@/lib/rag-lite";
import styles from "./rag-lite.module.css";

export function SearchCoverage({ coverage, allDocs, unavailable, busy, onCorpus, onRetry }: {
  coverage: RagCoverage | null; allDocs: boolean; unavailable: boolean; busy: boolean;
  onCorpus: () => void; onRetry: () => void;
}) {
  if (!coverage) return <section className={styles.coverage} aria-label="Search coverage">
    <h2>{allDocs ? "Corpus coverage" : "Selected asset coverage"}</h2>
    <p role="status">{unavailable ? "Coverage unavailable. Check the local service; evidence availability is unknown." : "Checking evidence coverage…"}</p>
    {unavailable && <button type="button" className="text-link" onClick={onRetry}>Retry coverage</button>}
  </section>;
  const d = coverage.diagnostics;
  return <section className={styles.coverage} aria-label="Search coverage">
    <h2>{allDocs ? "Corpus coverage · no asset attribution" : "Selected asset coverage"}</h2>
    <p>{!allDocs && d && <>{d.reviewed_attributes} reviewed technical attributes · {d.direct_documents} directly linked PDFs · </>}{coverage.searchable_documents} searchable PDFs · {coverage.image_only_documents} image-only PDFs</p>
    <details className={styles.options}>
      <summary>Coverage details</summary>
      <p>{coverage.authorized_documents} authorized originals · {coverage.searchable_pages} searchable physical pages · {coverage.unavailable_documents} unavailable or without usable text.</p>
      {d && <p>{d.not_authorized_documents} not authorized · {d.missing_documents} missing originals · {d.invalid_documents} invalid originals · {d.invalid_indexes} invalid indexes · {d.extraction_limited_documents} with limited extraction · {d.unknown_metadata_sources} sources with unknown date/authority.</p>}
      <p>Only direct reviewed links apply to a selected asset. Image-only PDFs remain retained but cannot be searched as text. No OCR is used.</p>
    </details>
    {!!d?.reason_codes.length && <ul>{d.reason_codes.map(code => evidenceReasonText(code)).filter(Boolean).map(message => <li key={message}>{message}</li>)}</ul>}
    {!allDocs && coverage.searchable_documents === 0 && <div className={styles.corpusOffer}>
      <p><strong>Corpus-wide search is not attributed to this asset.</strong> It may find evidence from other authorized originals.</p>
      <button type="button" className="text-link" disabled={busy} onClick={onCorpus}>Search all authorized PDFs</button>
    </div>}
  </section>;
}

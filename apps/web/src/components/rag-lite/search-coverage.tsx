import { evidenceReasonText, type RagCoverage } from "@/lib/rag-lite";
import styles from "./rag-lite.module.css";

export function SearchCoverage({ coverage, allDocs, unavailable, onRetry }: {
  coverage: RagCoverage | null; allDocs: boolean; unavailable: boolean; onRetry: () => void;
}) {
  if (!coverage) return <div className={styles.coverage}>
    <p role="status">{unavailable ? "Coverage unavailable; evidence availability is unknown." : "Checking coverage…"}</p>
    {unavailable && <button type="button" className="text-link" onClick={onRetry}>Retry coverage</button>}
  </div>;
  const d = coverage.diagnostics;
  return <div className={styles.coverage}>
    <h3>{allDocs ? "Corpus coverage" : "Selected asset coverage"}</h3>
    <p>{!allDocs && d && <>{d.reviewed_attributes} reviewed fields · {d.direct_documents} linked PDFs · </>}{coverage.searchable_documents} searchable · {coverage.image_only_documents} image-only</p>
    <p>{coverage.authorized_documents} authorized originals · {coverage.searchable_pages} searchable pages · {coverage.unavailable_documents} unavailable.</p>
    {d && <p>{d.unscoped_documents ?? 0} without reviewed passages · {d.not_authorized_documents} not authorized · {d.missing_documents} missing originals · {d.invalid_documents} invalid originals · {d.invalid_indexes} invalid indexes · {d.extraction_limited_documents} with limited text · {d.unknown_metadata_sources} sources with unknown metadata.</p>}
    {!!d?.reason_codes.length && <ul>{d.reason_codes.map(evidenceReasonText).filter(Boolean).map(message => <li key={message}>{message}</li>)}</ul>}
    <p>Only direct reviewed links apply. Image-only PDFs cannot be text searched; no OCR is used.</p>
  </div>;
}

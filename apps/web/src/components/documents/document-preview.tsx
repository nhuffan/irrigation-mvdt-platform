/* Local image Blob URLs intentionally bypass Next image optimization. */
/* eslint-disable @next/next/no-img-element */
"use client";
import { useEffect, useState } from "react";
import type { DocumentRecord } from "@/types/media";
import { documentMediaError, originalDocumentUrl } from "@/lib/document-preview";

export function DocumentPreview({ document: doc, initialPage = 1 }: { document: DocumentRecord; initialPage?: number }) {
  const [state, setState] = useState<{ id?: string; url?: string; error?: string }>({});
  const [attempt, setAttempt] = useState(0);
  const [embeddedError, setEmbeddedError] = useState(false);
  const pdf = doc.mime_type === "application/pdf";
  const image = ["image/png", "image/jpeg", "image/webp", "image/gif"].includes(doc.mime_type ?? "");
  const current = state.id === doc.id ? state : {};
  useEffect(() => {
    if (!pdf && !image) return;
    const abort = new AbortController();
    let url: string | undefined;
    async function load() {
      setState({ id: doc.id }); setEmbeddedError(false);
      try {
        const response = await fetch(`/api/media/documents/${doc.id}`, {
          cache: "no-store", signal: AbortSignal.any([abort.signal, AbortSignal.timeout(30000)]),
        });
        if (!response.ok) throw new Error(documentMediaError(response.status));
        const blob = await response.blob();
        if (abort.signal.aborted) return;
        url = URL.createObjectURL(blob); setState({ id: doc.id, url });
      } catch (error) {
        if (!abort.signal.aborted) setState({ id: doc.id, error: error instanceof Error ? error.message : documentMediaError(500) });
      }
    }
    void load();
    return () => { abort.abort(); if (url) URL.revokeObjectURL(url); };
  }, [doc.id, attempt, pdf, image]);
  return <div className="document-preview-frame">
    <div className="document-preview-toolbar">
      <a className="button button-secondary" href={originalDocumentUrl(doc.id, initialPage)} target="_blank" rel="noopener noreferrer">{pdf ? `Open original PDF (page ${initialPage})` : "Open original file"} ↗</a>
      <a className="text-link" href={`/api/media/documents/${doc.id}?download=true`} download={doc.original_file_name}>Download original</a>
    </div>
    {pdf && <p className="preview-fallback">If the embedded preview is blank, open the original above. Preview support does not determine evidence availability.</p>}
    <div className="document-preview-shell" aria-busy={(pdf || image) && !current.url && !current.error}>
      {current.error ? <div className="preview-status" role="alert"><h2>Original unavailable</h2><p>{current.error}</p><button className="button button-secondary" onClick={() => setAttempt(n => n + 1)}>Retry original</button></div>
        : !pdf && !image ? <p className="preview-status">This file type has no embedded preview. Open or download the original above.</p>
        : !current.url ? <div className="preview-status" role="status"><div className="skeleton-card" aria-hidden="true"/><p>Loading original…</p></div>
        : embeddedError ? <div className="preview-status" role="alert"><h2>Preview unavailable</h2><p>The original link remains available above.</p><button className="button button-secondary" onClick={() => setAttempt(n => n + 1)}>Retry preview</button></div>
        : pdf ? <iframe className="document-preview" title={doc.original_file_name} src={`${current.url}#page=${initialPage}`} onError={() => setEmbeddedError(true)}/>
        : <img className="document-image" src={current.url} alt={doc.source.title} onError={() => setEmbeddedError(true)}/>}
    </div>
  </div>;
}

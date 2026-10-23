/* Native img intentionally displays a local Blob URL without Next image optimization. */
/* eslint-disable @next/next/no-img-element */
"use client";
import { useEffect, useState } from "react";
import type { DocumentRecord } from "@/types/media";
export function DocumentPreview({
  document: doc,
}: {
  document: DocumentRecord;
}) {
  const [state, setState] = useState<{ url?: string; error?: string }>({});
  const [attempt, setAttempt] = useState(0);
  const preview =
    doc.mime_type === "application/pdf" ||
    ["image/png", "image/jpeg", "image/webp", "image/gif"].includes(
      doc.mime_type ?? "",
    );
  useEffect(() => {
    const abort = new AbortController();
    let url: string | undefined;
    async function load() {
      setState({});
      try {
        const response = await fetch(`/api/media/documents/${doc.id}`, {
          signal: AbortSignal.any([abort.signal, AbortSignal.timeout(30000)]),
        });
        if (!response.ok)
          throw new Error(
            response.status === 410
              ? "Document metadata exists, but the file is unavailable."
              : "Unable to load document.",
          );
        url = URL.createObjectURL(await response.blob());
        if (!abort.signal.aborted) setState({ url });
        else URL.revokeObjectURL(url);
      } catch (error) {
        if (!abort.signal.aborted)
          setState({
            error:
              error instanceof Error
                ? error.message
                : "Unable to load document.",
          });
      }
    }
    void load();
    return () => {
      abort.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [doc.id, attempt]);
  if (state.error)
    return (
      <div role="alert" className="panel">
        <p>{state.error}</p>
        <button onClick={() => setAttempt((n) => n + 1)}>Try again</button>
      </div>
    );
  if (!state.url) return <p role="status">Loading document…</p>;
  return (
    <div className="document-preview-frame">
      {!preview && (
        <p className="muted">
          Preview is unavailable for this file type. Download and open it
          externally.
        </p>
      )}
      {doc.mime_type === "application/pdf" && (
        <iframe
          className="document-preview"
          title={doc.original_file_name}
          src={state.url}
        />
      )}
      {preview && doc.mime_type !== "application/pdf" && (
        <img
          className="document-image"
          src={state.url}
          alt={doc.source.title}
        />
      )}
    </div>
  );
}

import Link from "next/link";
import type { DocumentRecord } from "@/types/media";
import { VerificationBadge } from "@/components/asset/source-info";
export function DocumentList({ documents }: { documents: DocumentRecord[] }) {
  if (!documents.length)
    return (
      <p className="muted mt-4">
        No documents are linked to this source or asset.
      </p>
    );
  return (
    <ul className="document-list">
      {documents.map((doc) => (
        <li className="panel" key={doc.id}>
          <h3>{doc.source.title}</h3>
          <p>{doc.original_file_name}</p>
          <p className="muted">
            {doc.source.source_type} ·{" "}
            {doc.source.source_date ?? "Date not available"} ·{" "}
            {doc.mime_type ?? "Unknown file type"}
          </p>
          <VerificationBadge status={doc.source.verification_status} />
          <Link className="text-link" href={`/documents/${doc.id}`}>
            Open document →
          </Link>
        </li>
      ))}
    </ul>
  );
}

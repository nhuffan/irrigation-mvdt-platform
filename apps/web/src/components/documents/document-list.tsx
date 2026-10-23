import { evidenceDisplayText } from "@/lib/evidence-display";
import { TechnicalMetadataPopover } from "@/components/asset/presentation";
import { DocumentLink } from "./document-link";
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
          <h3>{evidenceDisplayText(doc.source.title)}</h3>
          <p>{doc.original_file_name}</p>
          <p className="muted">
            {doc.source.source_type} ·{" "}
            {doc.source.source_date ?? "Date not available"} ·{" "}
            {doc.mime_type ?? "Unknown file type"}
          </p>
          <VerificationBadge status={doc.source.verification_status} /><TechnicalMetadataPopover fields={{"Document UUID":doc.id,"Source UUID":doc.source_id,"Document code":doc.document_code,"SHA-256":doc.checksum_sha256,"Page count":doc.page_count}}/>
          <DocumentLink className="text-link" href={`/documents/${doc.id}`}>
            Open document →
          </DocumentLink>
        </li>
      ))}
    </ul>
  );
}

import { TechnicalMetadataPopover } from "@/components/asset/presentation";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getDocument } from "@/lib/api";
import { SourceInfo } from "@/components/asset/source-info";
import { DocumentPreview } from "@/components/documents/document-preview";
export default async function DocumentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const doc = await getDocument(id).catch((error) => {
    if (error instanceof ApiError && [404, 422].includes(error.status))
      notFound();
    throw error;
  });
  return (
    <main className="page-shell">
      <Link
        className="text-link"
        href={`/reservoirs/${doc.source.reservoir_id}`}
      >
        ← Reservoir
      </Link>
      <div className="page-heading mt-6">
        <div>
          <p className="eyebrow">Document</p>
          <h1>{doc.original_file_name}</h1>
        </div>
      </div>
      <p className="muted">
        {doc.mime_type} · {doc.file_size ?? "Unknown"} bytes ·{" "}
        {doc.page_count ?? "Unknown"} pages
      </p>
      <TechnicalMetadataPopover fields={{"Document UUID":doc.id,"Document code":doc.document_code,"Source UUID":doc.source_id,"SHA-256":doc.checksum_sha256,MIME:doc.mime_type,"Page count":doc.page_count}}/>
      <SourceInfo source={doc.source} />
      <DocumentPreview document={doc} />
    </main>
  );
}

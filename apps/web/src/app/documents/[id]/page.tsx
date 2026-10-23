import { PanelSection } from "@/components/ui/panel-section";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { TechnicalMetadataPopover } from "@/components/asset/presentation";
import Link from "next/link";
import { documentReturnTo, documentBackLabel } from "@/lib/document-navigation";
import { notFound } from "next/navigation";
import { ApiError, getDocument } from "@/lib/api";
import { SourceInfo } from "@/components/asset/source-info";
import { DocumentPreview } from "@/components/documents/document-preview";
export default async function DocumentPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ returnTo?: string | string[] }>;
}) {
  const { id } = await params;
  const doc = await getDocument(id).catch((error) => {
    if (error instanceof ApiError && [404, 422].includes(error.status))
      notFound();
    throw error;
  });
  const returnTo = documentReturnTo((await searchParams).returnTo) ?? `/data-sources/${doc.source_id}/documents`;
  return (
    <main className="page-shell">
      <Link
        className="text-link"
        href={returnTo}
      >
        ← {documentBackLabel(returnTo)}
      </Link>
      <div className="page-heading mt-6">
        <div>
          <p className="eyebrow">Document</p>
          <h1>{evidenceDisplayText(doc.original_file_name)}</h1>
        </div>
      </div>
      <div className="document-workspace"><div className="document-content"><DocumentPreview document={doc}/></div><aside className="document-inspector"><PanelSection title="Document details">
      <p className="muted">
        {doc.mime_type} · {doc.file_size ?? "Unknown"} bytes ·{" "}
        {doc.page_count ?? "Unknown"} pages
      </p>
      <a className="text-link document-download" href={`/api/media/documents/${doc.id}?download=true`} download={doc.original_file_name}>Download original</a>
      <TechnicalMetadataPopover fields={{"Document UUID":doc.id,"Document code":doc.document_code,"Source UUID":doc.source_id,"SHA-256":doc.checksum_sha256,MIME:doc.mime_type,"Page count":doc.page_count}}/>
      <SourceInfo source={doc.source} />
      </PanelSection></aside></div>

    </main>
  );
}

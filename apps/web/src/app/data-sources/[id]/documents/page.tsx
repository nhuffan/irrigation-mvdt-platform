import Link from "next/link";
import { documentReturnTo, documentBackLabel } from "@/lib/document-navigation";
import { notFound } from "next/navigation";
import { ApiError, getResearchSource, getSourceDocuments } from "@/lib/api";
import { DocumentList } from "@/components/documents/document-list";
import { PageHeader } from "@/components/ui/page-header";
import { SourceInfo, VerificationBadge } from "@/components/asset/source-info";
import { linkedDocumentCounts, publicEvidenceText } from "@/lib/asset-information";
import { evidenceDisplayText } from "@/lib/evidence-display";

export default async function SourceDocuments({
  params, searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ returnTo?: string | string[] }>;
}) {
  const { id } = await params;
  const [source, documents] = await Promise.all([
    getResearchSource(id),
    getSourceDocuments(id),
  ]).catch((error) => {
    if (error instanceof ApiError && [404, 422].includes(error.status))
      notFound();
    throw error;
  });
  const counts = linkedDocumentCounts(documents);
  const returnTo = documentReturnTo((await searchParams).returnTo) ?? `/reservoirs/${source.reservoir_id}#assets`;
  return (
    <main className="page-shell">
      <Link className="text-link" href={returnTo}>← {documentBackLabel(returnTo)}</Link>
      <PageHeader eyebrow="Source inventory" title="Source documents"
        description="Source identity and available document metadata. A source entry does not establish retained file bytes or an asset–document association." />
      <section className="panel" aria-label="Source inventory identity">
        <p className="eyebrow">{source.source_code}</p>
        <h2>{evidenceDisplayText(publicEvidenceText(source.title))}</h2>
        <p className="muted">{source.source_type} · Source date: {source.source_date ?? "Not available"} · Authority: {publicEvidenceText(source.authority_level?.trim() || "UNKNOWN")}</p>
        <VerificationBadge status={source.verification_status} />
        <SourceInfo source={source} />
      </section>
      <section className="panel mt-6" aria-labelledby="source-documents-heading">
        <h2 id="source-documents-heading">Document availability</h2>
        <p className="summary-note">{counts.edges} source–document metadata records · {counts.distinctPdfHashes ?? "Unavailable"} distinct PDF hashes in that metadata. These counts are not asset–document links or the study-wide source denominator; metadata and a recorded hash do not certify retained bytes.</p>
        {documents.length === 0 && <p className="muted mt-3">This source is registered in the inventory, but no document metadata is registered for it. Its source-reported technical fields remain traceable by source code and exact locator; no downloadable PDF is inferred.</p>}
        <DocumentList documents={documents} />
      </section>
    </main>
  );
}

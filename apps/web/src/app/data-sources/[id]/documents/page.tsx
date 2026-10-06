import { notFound } from "next/navigation";
import { ApiError, getSourceDocuments } from "@/lib/api";
import { DocumentList } from "@/components/documents/document-list";
export default async function SourceDocuments({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const documents = await getSourceDocuments(id).catch((error) => {
    if (error instanceof ApiError && [404, 422].includes(error.status))
      notFound();
    throw error;
  });
  return (
    <main className="page-shell">
      <h1>Source documents</h1>
      <DocumentList documents={documents} />
    </main>
  );
}

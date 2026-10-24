import Link from "next/link";
import { documentReturnTo, documentBackLabel } from "@/lib/document-navigation";
import { publicModels } from "@/lib/public-client-data";
import { PageHeader } from "@/components/ui/page-header";
import { notFound } from "next/navigation";
import { ApiError, getReservoir, getModels } from "@/lib/api";
import { ModelBrowser } from "@/components/three-d/model-browser";
export default async function ThreeDPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ model?: string; object?: string; paper?: string; returnTo?: string | string[] }>;
}) {
  const { id } = await params;
  const query = await searchParams;
  const [, models] = await Promise.all([
    getReservoir(id),
    getModels(id),
  ]).catch((error) => {
    if (error instanceof ApiError && [404, 422].includes(error.status))
      notFound();
    throw error;
  });
  if (query.model && !models.some(m => m.id === query.model)) notFound();
  return (
    <main className={query.paper==="1"?"page-shell model-page clean-paper":"page-shell model-page"}>
      {documentReturnTo(query.returnTo) && <Link className="text-link" href={documentReturnTo(query.returnTo)!}>← {documentBackLabel(documentReturnTo(query.returnTo)!)}</Link>}
      <PageHeader eyebrow="Representation" title="3D Models" description="A representative 3D view for exploring linked assets and evidence. Model appearance and placement do not certify surveyed geometry, building identity or present asset condition." />
      <ModelBrowser
        models={publicModels(models)}
        initialModel={query.model}
        initialObject={query.object}
      />
    </main>
  );
}

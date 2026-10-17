import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getReservoir, getModels } from "@/lib/api";
import { ModelBrowser } from "@/components/three-d/model-browser";
export default async function ThreeDPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ model?: string; object?: string; paper?: string }>;
}) {
  const { id } = await params;
  const query = await searchParams;
  const [reservoir, models] = await Promise.all([
    getReservoir(id),
    getModels(id),
  ]).catch((error) => {
    if (error instanceof ApiError && [404, 422].includes(error.status))
      notFound();
    throw error;
  });
  return (
    <main className={query.paper==="1"?"page-shell model-page clean-paper":"page-shell model-page"}>
      <Link className="text-link" href={`/reservoirs/${id}`}>
        ← Reservoir & GIS
      </Link>
      <div className="page-heading mt-6">
        <div>
          <p className="eyebrow">3D representation</p>
          <h1>{reservoir.name}</h1>
        </div>
      </div>
      <ModelBrowser
        models={models}
        initialModel={query.model}
        initialObject={query.object}
      />
    </main>
  );
}

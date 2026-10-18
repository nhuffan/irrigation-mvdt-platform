import { TechnicalMetadataPopover } from "@/components/asset/presentation";
import { Suspense } from "react";
import { ReservoirAssets } from "@/components/asset/reservoir-assets";
import { PageHeader } from "@/components/ui/page-header";
import { notFound } from "next/navigation";
import { ApiError, getReservoir } from "@/lib/api";
export const dynamic = "force-dynamic";
export default async function ReservoirPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
  )
    notFound();
  const reservoir = await getReservoir(id).catch((error) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });
  return (
    <main className="page-shell">
      <PageHeader eyebrow="Reservoir" title="Overview"
        description={<>{reservoir.name} · {reservoir.code} · {reservoir.province ?? "Unknown province"}</>} />
      <details className="reservoir-metadata"><summary>Reservoir context</summary><div className="registry-grid">
        <section className="panel">
          <p className="eyebrow">Location</p>
          <h2>Geographic reference</h2><p className="summary-note">Reservoir navigation context only; not verified asset geometry.</p>
          <dl className="detail-list">
            <div>
              <dt>Latitude</dt>
              <dd>{reservoir.latitude}</dd>
            </div>
            <div>
              <dt>Longitude</dt>
              <dd>{reservoir.longitude}</dd>
            </div>
            <div>
              <dt>Coordinate system</dt>
              <dd>WGS 84 · EPSG:4326</dd>
            </div>
            <div>
              <dt>Reservoir ID</dt>
              <dd><TechnicalMetadataPopover fields={{"Reservoir UUID":reservoir.id}}/></dd>
            </div>
          </dl>
        </section>
      </div>
      {reservoir.description && (
        <section className="panel mt-6">
          <p className="eyebrow">About this reservoir</p>
          <h2>Description</h2>
          <p className="muted mt-3">{reservoir.description}</p>
        </section>
      )}
      </details>
      <Suspense
        fallback={
          <section className="panel mt-10" role="status">
            Loading reservoir assets…
          </section>
        }
      >
        <ReservoirAssets reservoir={reservoir} />
      </Suspense>
    </main>
  );
}

import { Suspense } from "react";
import { ReservoirAssets } from "@/components/asset/reservoir-assets";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getReservoir } from "@/lib/api";
import { MvdtReadiness } from "@/components/reservoir/mvdt-readiness";
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
      <Link className="text-link" href="/map">
        ← Back to GIS map
      </Link>
      <div className="page-heading mt-8">
        <div>
          <p className="eyebrow">Reservoir overview · {reservoir.code}</p>
          <h1>{reservoir.name}</h1>
          <p className="muted mt-3">
            {reservoir.province ?? "Unknown province"}
          </p>
        </div>
        <span className="level-badge">MVDT Level {reservoir.mvdt_level}</span>
      </div>
      <Link className="text-link" href={`/reservoirs/${id}/3d`}>
        Open 3D models →
      </Link>
      <div className="registry-grid">
        <MvdtReadiness
          level={reservoir.mvdt_level}
          status={reservoir.data_status}
        />
        <section className="panel">
          <p className="eyebrow">Location</p>
          <h2>Geographic reference</h2>
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
              <dd className="break-all text-sm">{reservoir.id}</dd>
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

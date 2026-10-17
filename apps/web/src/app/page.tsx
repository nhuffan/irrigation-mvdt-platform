import Link from "next/link";
import { getReservoirs } from "@/lib/api";
import { StatusBadge } from "@/components/reservoir/status-badge";
export const dynamic = "force-dynamic";
export default async function HomePage() {
  const reservoirs = await getReservoirs();
  const development = reservoirs.filter(r => /^(DEMO|DEV)/.test(r.code));
  const visible = reservoirs.filter(r => !development.includes(r));
  return (
    <main className="page-shell">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Reservoir registry</p>
          <h1>Reservoir registry</h1>
        </div>
        <Link className="button" href="/map">
          Explore GIS map <span aria-hidden="true">↗</span>
        </Link>
      </div>
      <div className="section-heading">
        <h2>Registered reservoirs</h2>
        <span className="muted">{visible.length} reservoirs</span>
      </div>
      {visible.length === 0 ? (
        <section className="panel">No reservoirs available.</section>
      ) : (
        <div className="registry-grid">
          {visible.map((r) => (
            <article className="panel reservoir-card" key={r.id}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="eyebrow">{r.code}</p>
                <StatusBadge status={r.data_status} />
              </div>
              <h2 className="mt-5">
                <Link href={`/reservoirs/${r.id}`}>{r.name}</Link>
              </h2>
              <p className="muted mt-2">{r.province ?? "Unknown province"}</p>
              <dl className="card-details">
                <div>
                  <dt>Maturity</dt>
                  <dd>Level {r.mvdt_level}</dd>
                </div>
                <div>
                  <dt>Latitude / Longitude</dt>
                  <dd>
                    {r.latitude}, {r.longitude}
                  </dd>
                </div>
              </dl>
              <Link className="text-link" href={`/reservoirs/${r.id}`}>
                View Reservoir <span aria-hidden="true">→</span>
              </Link>
            </article>
          ))}
        </div>
      )}
    {development.length > 0 && <details className="reservoir-metadata"><summary>Development data · {development.length} reservoirs</summary><p className="summary-note">Synthetic records for development, not research evidence.</p>{development.map(r => <p key={r.id}><Link className="text-link" href={`/reservoirs/${r.id}`}>{r.code} · {r.name}</Link></p>)}</details>}
    </main>
  );
}

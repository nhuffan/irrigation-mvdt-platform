export function ViewPending({ title, workspace = false }: { title: string; workspace?: boolean }) {
  return <main className="page-shell view-pending" aria-busy="true">
    <h1>{title}</h1><p className="muted" role="status">Loading the latest information…</p>
    <div className={`pending-grid ${workspace ? "pending-workspace" : ""}`} aria-hidden="true">
      <div className="panel"><div className="skeleton-line"/><div className="skeleton-line"/><div className="skeleton-card"/></div>
      <div className="panel"><div className="skeleton-line"/><div className="skeleton-card"/></div>
    </div>
  </main>;
}

export function PanelPending({ label }: { label: string }) {
  return <section className="pending-section" role="status" aria-busy="true"><p className="muted">{label}</p><div className="pending-grid pending-workspace" aria-hidden="true"><div className="panel"><div className="skeleton-line"/><div className="skeleton-card"/></div><div className="panel"><div className="skeleton-card"/></div></div></section>;
}

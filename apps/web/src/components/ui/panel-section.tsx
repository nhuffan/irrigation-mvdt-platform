import type { ReactNode } from "react";
export function PanelSection({ title, children, description, actions }: { title: string; children: ReactNode; description?: string; actions?: ReactNode }) {
  return <section className="panel-section">
    <header className="panel-section-heading"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{actions}</header>
    <div className="panel-section-body">{children}</div>
  </section>;
}
export function PanelDisclosure({ title, children, open = false }: { title: string; children: ReactNode; open?: boolean }) {
  return <details className="panel-disclosure" open={open}><summary>{title}</summary><div className="panel-section-body">{children}</div></details>;
}
export function MetricCard({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return <div className="metric-card"><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</div>;
}

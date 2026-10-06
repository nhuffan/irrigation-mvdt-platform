import { MATURITY } from "@/lib/reservoir-status";
import { StatusBadge } from "./status-badge";
export function MvdtReadiness({
  level,
  status,
}: {
  level: number;
  status: string;
}) {
  const maturity = MATURITY[level];
  return (
    <section className="panel">
      <p className="eyebrow">Data readiness</p>
      <h2>
        Level {level} · {maturity?.title ?? "Unclassified"}
      </h2>
      <StatusBadge status={status} />
      <p className="muted mt-4">
        {maturity?.description ?? "This level has not been classified."}
      </p>
    </section>
  );
}

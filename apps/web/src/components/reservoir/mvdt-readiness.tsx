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
      {level >= 3 && (
        <div className="mt-6 border-t border-slate-200 pt-4">
          <p className="text-sm font-semibold">Future modules</p>
          <p className="muted mt-2 text-sm">O&M · Documents</p>
          <p className="muted mt-2 text-sm">
            These modules are planned for later stages and are not available
            yet.
          </p>
        </div>
      )}
    </section>
  );
}

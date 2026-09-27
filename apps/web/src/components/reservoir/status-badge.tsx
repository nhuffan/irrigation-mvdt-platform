import { statusColor, statusLabel } from "@/lib/reservoir-status";
export function StatusBadge({ status }: { status: string }) {
  return (
    <span className="status-badge" style={{ color: statusColor(status) }}>
      <span
        aria-hidden="true"
        className="status-dot"
        style={{ background: statusColor(status) }}
      />
      {statusLabel(status)}
    </span>
  );
}

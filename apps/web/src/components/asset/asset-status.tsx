import type { Asset } from "@/types/asset";
const STATUSES = {
  REGISTERED: { label: "Registered", color: "#64748b" },
  PARTIAL: { label: "Partial data", color: "#b45309" },
  VERIFIED: { label: "Verified", color: "#047857" },
};
export function AssetStatus({ status }: { status: Asset["data_status"] }) {
  const item = STATUSES[status];
  return (
    <span className="status-badge" style={{ color: item.color }}>
      <span
        aria-hidden="true"
        className="status-dot"
        style={{ background: item.color }}
      />
      {item.label}
    </span>
  );
}

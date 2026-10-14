import type { Asset } from "@/types/asset";
import { assetDisplayName } from "@/lib/asset-display";
export function AssetDisplayName({ asset }: { asset: Asset }) { return <>{assetDisplayName(asset)}</>; }
export function StatusBadge({ children }: { children: React.ReactNode }) { return <span className="presentation-badge">{children}</span>; }
export function TechnicalMetadataPopover({ fields, label = "Chi tiết — Technical details" }: { fields: Record<string, string | number | null | undefined>; label?: string }) {
  const rows = Object.entries(fields).filter(([,v]) => v !== null && v !== undefined && v !== "");
  if (!rows.length) return null;
  return <details className="technical-metadata"><summary>{label}</summary><dl>{rows.map(([key,value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl></details>;
}
export function AssetMetadata({ asset }: { asset: Asset }) { return <TechnicalMetadataPopover fields={{"Asset code":asset.asset_code,"Asset UUID":asset.id,"Canonical name":asset.name,"Reservoir UUID":asset.reservoir_id,"Parent UUID":asset.parent_asset_id,"Identity status":asset.data_status}} />; }

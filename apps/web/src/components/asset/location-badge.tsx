import type { Asset } from "@/types/asset";
import { assetLocation } from "@/lib/asset-location";
export function LocationBadge({ asset }: { asset: Asset }) {
  const status = assetLocation(asset).location_status;
  return <span className={`location-badge location-${status.toLowerCase()}`}>{status.replaceAll("_", " ")}</span>;
}

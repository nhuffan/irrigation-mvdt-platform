import type { Asset } from "@/types/asset";
import { spatialDisposition } from "@/lib/asset-location";
import styles from "./spatial-coverage.module.css";
export function LocationBadge({ asset }: { asset: Asset }) {
  const status = spatialDisposition(asset);
  const extra = status === "CANDIDATE_NEEDS_REVIEW" ? styles.candidate : status === "CONFLICTED" ? styles.conflicted : status === "NO_DEFENSIBLE_LOCATION" ? styles.missing : "";
  return <span className={`location-badge location-${status.toLowerCase()} ${extra}`}>{(status === "NO_DEFENSIBLE_LOCATION" ? "NO LOCATION" : status.replaceAll("_", " "))}</span>;
}

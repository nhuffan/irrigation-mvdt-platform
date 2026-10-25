import type { Asset } from "@/types/asset";
import { spatialCoverage, assetLocation, hierarchy } from "@/lib/asset-location";
import { assetDisplayName } from "@/lib/asset-display";
import { OriginLink } from "@/components/documents/document-link";
import { LocationBadge } from "./location-badge";
import { AssetLocationSummary } from "./asset-location-summary";
import styles from "./spatial-coverage.module.css";

export function SpatialCoverage({ assets, onSelect, onFilter, activeFilter }: {
  assets: Asset[];
  onSelect?: (asset: Asset) => void;
  onFilter?: (filter: string) => void;
  activeFilter?: string;
}) {
  const coverage = spatialCoverage(assets);
  const metrics = [
    {label:"Accepted references", value:coverage.reference, filter:"REFERENCE_LOCATION"},
    {label:"Verified geometries", value:coverage.verified, filter:"VERIFIED_GEOMETRY"},
    {label:"Unresolved candidates", value:coverage.unresolved, filter:"UNRESOLVED"},
    {label:"No location", value:coverage.missing, filter:"NO_DEFENSIBLE_LOCATION"},
  ];
  return <section className={styles.coverage} aria-label="Spatial coverage">
    <div className={styles.heading}><h2>Spatial coverage</h2><span>{coverage.total} registered assets</span></div>
    <div className={styles.metrics}>{metrics.map(metric => {
      const content = <><strong>{coverage.unavailable ? "Unavailable" : metric.value}</strong><span>{metric.label}</span></>;
      return onFilter ? <button type="button" key={metric.filter} className={styles.metric} aria-pressed={activeFilter === metric.filter} onClick={() => onFilter(activeFilter === metric.filter ? "all" : metric.filter)}>{content}</button> : <div key={metric.filter} className={styles.metric}>{content}</div>;
    })}</div>
    {coverage.unavailable > 0 && <p className={styles.note} role="status">Location review is unavailable for {coverage.unavailable} asset(s). Coverage totals cannot be confirmed.</p>}
    <details className={styles.evidence}><summary>Evidence and unresolved locations</summary>
      <p className={styles.note}>Candidates have no map pin. Parent assets keep their own evidence; child locations are not inherited.</p>
      <ul className={styles.list}>{assets.map(asset => {
        const location = assetLocation(asset);
        const {ancestors} = hierarchy(assets, asset);
        return <li key={asset.id}><div className={styles.row}><div><strong>{assetDisplayName(asset)}</strong>{ancestors.length > 0 && <p className={styles.note}>Component of {assetDisplayName(ancestors[ancestors.length - 1])}</p>}<LocationBadge asset={asset}/></div>
          {onSelect ? <button type="button" className="text-link" aria-label={`Inspect ${assetDisplayName(asset)}`} onClick={() => { onSelect(asset); requestAnimationFrame(() => { const panel = document.getElementById("selected-asset-panel"); panel?.scrollIntoView({block:"nearest"}); panel?.focus(); }); }}>Inspect asset →</button> : <OriginLink className="text-link" href={`/reservoirs/${asset.reservoir_id}?asset=${asset.id}#asset-gis`}>Inspect in Asset GIS →</OriginLink>}
        </div>{location.reason && (location.location_status === "NO_LOCATION" || !!location.candidate_count) && <p>{location.reason}</p>}
        <details className={styles.evidence}><summary>Location evidence</summary><AssetLocationSummary asset={asset} anchor={false}/></details>
        </li>;
      })}</ul>
    </details>
  </section>;
}

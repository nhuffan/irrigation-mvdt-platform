import { MetricCard } from "@/components/ui/panel-section";
import Link from "next/link";
import { dataset } from "@/lib/explorer-state";
import { descendantIds, hierarchyCoverage, l2Count, type TechnicalRecords } from "@/lib/asset-hierarchy";
import type { Asset } from "@/types/asset";
import { AssetDisplayName } from "./presentation";
export function AssetHierarchy({ assets, selected, records }: { assets: Asset[]; selected: Asset; records: TechnicalRecords }) {
  const scoped = assets.filter(a => dataset(a) === dataset(selected));
  const totals = hierarchyCoverage(scoped, records);
  const display = (n: number | null) => n === null ? "Unavailable" : n;
  const render = (asset: Asset, ancestors: string[] = []): React.ReactNode => {
    if (ancestors.includes(asset.id)) return null;
    return <li key={asset.id}>
      <Link className="text-link" aria-current={asset.id === selected.id ? "page" : undefined} href={`/assets/${asset.id}`}><AssetDisplayName asset={asset}/></Link>
      <p className="muted text-sm">Direct L2: {display(l2Count([asset.id], records))} · Descendant L2: {display(l2Count(descendantIds(scoped, asset.id), records))}</p>
      <ul>{scoped.filter(a => a.parent_asset_id === asset.id).map(a => render(a, [...ancestors, asset.id]))}</ul>
    </li>;
  };
  return <section aria-label="Asset hierarchy and L2 coverage">
    <h3>Asset hierarchy</h3>
    <div className="hierarchy-metrics"><MetricCard label="Primary L2" value={display(totals.primary)}/><MetricCard label="Component L2" value={display(totals.components)}/><MetricCard label="All-tree L2" value={display(totals.all)}/></div>
    <p className="summary-note">Descendant totals summarize child records; values and provenance stay with each child. Scope: {dataset(selected)}.</p>
    <ul className="asset-hierarchy">{scoped.filter(a => !a.parent_asset_id || !scoped.some(p => p.id === a.parent_asset_id)).map(a => render(a))}</ul>
  </section>;
}

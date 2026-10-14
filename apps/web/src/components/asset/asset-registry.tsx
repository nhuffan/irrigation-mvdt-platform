import { AssetSymbol } from "./asset-symbol";
import { AssetDisplayName, AssetMetadata } from "./presentation";
import { LocationBadge } from "./location-badge";
import Link from "next/link";
import type { Asset } from "@/types/asset";
import type { ExplorerRecords } from "@/lib/explorer-data";
import { modelHref } from "@/lib/explorer-state";
export function AssetRegistry({ assets, records, selectedId, onSelect }: { assets: Asset[]; records: ExplorerRecords; selectedId?: string; onSelect: (asset: Asset) => void }) {
  return <div className="asset-table-wrap"><table className="asset-table"><caption className="sr-only">Reservoir asset registry</caption>
    <thead><tr><th scope="col">Asset / type</th><th scope="col">Status / location</th><th scope="col">Records</th><th scope="col">Actions</th></tr></thead><tbody>
    {assets.map(a => <tr key={a.id} className={a.id === selectedId ? "selected-asset" : ""} aria-selected={a.id === selectedId}>
      <th scope="row"><button className="text-link" onClick={() => onSelect(a)}><AssetSymbol category={a.category.code}/><AssetDisplayName asset={a}/></button><span className="asset-code">{a.category.name}</span><AssetMetadata asset={a}/></th>
      <td>{a.data_status}<br /><LocationBadge asset={a} /></td>
      <td>{records[a.id].technical?.length ?? "Unavailable"} technical<br />{records[a.id].events?.length ?? "Unavailable"} verified O&M<br />{records[a.id].links?.length ?? "Unavailable"} 3D links</td>
      <td><div className="explorer-actions"><button className="text-link" onClick={() => onSelect(a)}>Select</button><button className="text-link" onClick={() => { onSelect(a); document.getElementById("asset-gis")?.scrollIntoView({ behavior: "smooth", block: "center" }); }}>View on Map</button><Link className="text-link" href={`/assets/${a.id}`}>View Detail</Link>{records[a.id].links?.map(l => <Link className="text-link" key={l.id} href={modelHref(a,l)}>View 3D</Link>)}</div></td>
    </tr>)}</tbody></table>{!assets.length && <p className="panel">No assets match these filters.</p>}</div>;
}

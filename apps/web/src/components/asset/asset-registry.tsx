import Link from "next/link";
import type { Asset } from "@/types/asset";
import type { ExplorerRecords } from "@/lib/explorer-data";
import { modelHref } from "@/lib/explorer-state";
export function AssetRegistry({ assets, records, selectedId, onSelect }: { assets: Asset[]; records: ExplorerRecords; selectedId?: string; onSelect: (asset: Asset) => void }) {
  return <div className="asset-table-wrap"><table className="asset-table"><caption className="sr-only">Reservoir asset registry</caption>
    <thead><tr><th scope="col">Asset / type</th><th scope="col">Status / geometry</th><th scope="col">Records</th><th scope="col">Actions</th></tr></thead><tbody>
    {assets.map(a => <tr key={a.id} className={a.id === selectedId ? "selected-asset" : ""} aria-selected={a.id === selectedId}>
      <th scope="row"><button className="text-link" onClick={() => onSelect(a)}>{a.name}</button><span className="asset-code">{a.asset_code} · {a.category.name}</span></th>
      <td>{a.data_status}<span className="asset-code">{a.geometry?.type ?? "Geometry unavailable"}</span></td>
      <td>{records[a.id].technical?.length ?? "Unavailable"} technical<br />{records[a.id].events?.length ?? "Unavailable"} verified O&M<br />{records[a.id].links?.length ?? "Unavailable"} 3D links</td>
      <td><div className="explorer-actions"><button className="text-link" onClick={() => onSelect(a)}>Select</button><button className="text-link" onClick={() => { onSelect(a); document.getElementById("asset-gis")?.scrollIntoView({ behavior: "smooth", block: "center" }); }}>View on Map</button><Link className="text-link" href={`/assets/${a.id}`}>View Detail</Link>{records[a.id].links?.map(l => <Link className="text-link" key={l.id} href={modelHref(a,l)}>View 3D</Link>)}</div></td>
    </tr>)}</tbody></table>{!assets.length && <p className="panel">No assets match these filters.</p>}</div>;
}

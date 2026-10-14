import { Suspense } from "react";
import Link from "next/link";
import { getReservoir, getReservoirAssets } from "@/lib/api";
import { getExplorerData } from "@/lib/explorer-data";
import type { Asset } from "@/types/asset";
import { AssetOm } from "./asset-om";
import { AssetMedia } from "./asset-media";
import { AssetDisplayName, AssetMetadata, StatusBadge } from "./presentation";
import { AssetLocationSummary } from "./asset-location-summary";
import { AssetInformationCoverage } from "./asset-information-coverage";
import { AssetEvidenceSummary } from "./asset-evidence-summary";
export async function AssetDetail({asset}:{asset:Asset}) {
 const [reservoir,assets,data]=await Promise.all([getReservoir(asset.reservoir_id),getReservoirAssets(asset.reservoir_id).catch(()=>null),getExplorerData(asset.id)]);
 const parent=assets?.find(a=>a.id===asset.parent_asset_id);const children=assets?.filter(a=>a.parent_asset_id===asset.id);
 return <div className="asset-properties-layout">
 <aside className="panel component-tree"><h2>Bộ phận — Components</h2>{parent&&<Link className="text-link" href={`/assets/${parent.id}`}><AssetDisplayName asset={parent}/></Link>}<p className="selected-component"><AssetDisplayName asset={asset}/></p>{children?.map(a=><p key={a.id}><Link className="text-link" href={`/assets/${a.id}`}><AssetDisplayName asset={a}/></Link></p>)}{assets===null?<p>Hierarchy unavailable</p>:!children?.length&&<p className="muted">No controlled child components recorded.</p>}<AssetMetadata asset={asset}/><Link className="text-link" href={`/map?paper=1&asset=${asset.id}`}>Bản đồ — GIS →</Link></aside>
 <div className="asset-properties"><section className="panel"><h2>Thông tin cơ bản — Overview</h2><StatusBadge>{asset.asset_code.startsWith("RS-")?"RS":asset.asset_code.startsWith("DEV-")?"DEV":"Unclassified"}</StatusBadge><p>{asset.category.name} · {reservoir.name}</p><p className="muted">{asset.description??"Description unavailable."}</p><AssetLocationSummary asset={asset}/></section>
 <div className="asset-summary-grid" id="coverage"><AssetInformationCoverage asset={asset} data={data}/><div className="panel"><AssetEvidenceSummary asset={asset} data={data}/></div></div>
 <Suspense fallback={<p>Loading technical and O&M information…</p>}><AssetOm assetId={asset.id}/></Suspense>
 <Suspense fallback={<p>Loading documents and model links…</p>}><AssetMedia assetId={asset.id} reservoirId={asset.reservoir_id}/></Suspense>
 </div></div>;
}

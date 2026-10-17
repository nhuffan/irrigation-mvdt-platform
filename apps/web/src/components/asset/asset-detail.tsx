import { AssetHierarchy } from "./asset-hierarchy";
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
 const parent=assets?.find(a=>a.id===asset.parent_asset_id);
 return <div className="asset-properties-layout">
 <aside className="panel component-tree"><p className="selected-component"><AssetDisplayName asset={asset}/></p>{assets===null&&<p>Hierarchy unavailable</p>}{assets && <Suspense fallback={<p>Loading hierarchy coverage…</p>}><AssetHierarchy assets={assets} selected={asset}/></Suspense>}<AssetMetadata asset={asset}/><Link className="text-link" href={`/map?paper=1&asset=${asset.id}`}>GIS →</Link></aside>
 <div className="asset-properties"><nav className="om-nav" aria-label="Evidence sections"><a href="#technical">Technical</a><a href="#sources">Sources</a><a href="#location">Location</a><a href="#timeline">O&amp;M</a><a href="#model">3D</a></nav>{parent && <nav aria-label="Parent breadcrumb"><Link className="text-link" href={`/assets/${parent.id}`}><AssetDisplayName asset={parent}/></Link> / <AssetDisplayName asset={asset}/></nav>}<section className="panel"><h2>Overview</h2><StatusBadge>{asset.asset_code.startsWith("RS-")?"RS":asset.asset_code.startsWith("DEV-")?"DEV":"Unclassified"}</StatusBadge><p>{asset.category.name} · {reservoir.name}</p><p className="muted">{asset.description??"Description unavailable."}</p><AssetLocationSummary asset={asset}/></section>
 <div className="asset-summary-grid" id="coverage"><AssetInformationCoverage asset={asset} data={data}/><div className="panel" id="sources"><AssetEvidenceSummary asset={asset} data={data}/></div></div>
 <Suspense fallback={<p>Loading technical and O&M information…</p>}><AssetOm assetId={asset.id}/></Suspense>
 <Suspense fallback={<p>Loading documents and model links…</p>}><AssetMedia assetId={asset.id} reservoirId={asset.reservoir_id}/></Suspense>
 </div></div>;
}

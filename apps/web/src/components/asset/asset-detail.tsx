import { PanelSection, PanelDisclosure } from "@/components/ui/panel-section";
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
 <aside className="component-tree">
 <PanelSection title="Current asset"><AssetDisplayName asset={asset}/><AssetMetadata asset={asset}/><Link className="text-link" href={`/map?asset=${asset.id}`}>Open on GIS →</Link></PanelSection>
 <PanelSection title="Asset navigation">{assets===null?<p>Hierarchy unavailable</p>:<Suspense fallback={<p>Loading hierarchy coverage…</p>}><AssetHierarchy assets={assets} selected={asset}/></Suspense>}</PanelSection>
 </aside>
 <div className="asset-properties"><nav className="om-nav" aria-label="Evidence sections"><a href="#technical">Technical</a><a href="#sources">Sources</a><a href="#location">Location</a><a href="#timeline">O&amp;M</a><a href="#model">3D</a></nav>{parent && <nav aria-label="Parent breadcrumb"><Link className="text-link" href={`/assets/${parent.id}`}><AssetDisplayName asset={parent}/></Link> / <AssetDisplayName asset={asset}/></nav>}<section className="panel"><h2>Overview</h2><StatusBadge>{"RS"}</StatusBadge><p>{asset.category.name} · {reservoir.name}</p><PanelDisclosure title="Asset notes"><p className="muted">{asset.description??"Description unavailable."}</p></PanelDisclosure><AssetLocationSummary asset={asset}/></section>
 <div className="asset-summary-grid" id="coverage"><AssetInformationCoverage asset={asset} data={data}/><div className="panel" id="sources"><AssetEvidenceSummary asset={asset} data={data}/></div></div>
 <Suspense fallback={<p>Loading technical and O&M information…</p>}><AssetOm assetId={asset.id}/></Suspense>
 <Suspense fallback={<p>Loading documents and model links…</p>}><AssetMedia assetId={asset.id} reservoirId={asset.reservoir_id}/></Suspense>
 </div></div>;
}

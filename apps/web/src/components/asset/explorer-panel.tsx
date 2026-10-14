import Link from "next/link";
import { modelHref, reviewedPreview, dataset } from "@/lib/explorer-state";
import { hierarchy } from "@/lib/asset-location";
import type { Asset } from "@/types/asset";
import type { ExplorerData } from "@/lib/explorer-data";
import { AssetDisplayName, AssetMetadata, TechnicalMetadataPopover, StatusBadge } from "./presentation";
import { AssetLocationSummary } from "./asset-location-summary";
import { AssetInformationCoverage } from "./asset-information-coverage";
import { AssetEvidenceSummary } from "./asset-evidence-summary";
export function ExplorerPanel({asset,assets,data,onSelect,paper}:{asset:Asset;assets:Asset[];data:ExplorerData;onSelect:(asset:Asset)=>void;paper?:boolean}) {
 const technical=reviewedPreview(data);const {ancestors,children}=hierarchy(assets,asset);
 return <aside id="selected-asset-panel" className={`panel explorer-panel${paper ? " evidence-first-panel" : ""}`} aria-label="Selected asset information" tabIndex={-1}>
 <p className="eyebrow">Thông tin tài sản — Asset information · {dataset(asset)==="research"?"RS":dataset(asset)==="development"?"DEV":"Unclassified"}</p>
 <nav aria-label="Asset hierarchy">{ancestors.map(a=><button className="text-link" key={a.id} onClick={()=>onSelect(a)}><AssetDisplayName asset={a}/> / </button>)}</nav>
 <h2><AssetDisplayName asset={asset}/></h2><p className="muted">{asset.category.name}</p><AssetMetadata asset={asset}/>
 {children.map(a=><button className="text-link" key={a.id} onClick={()=>onSelect(a)}>Component · <AssetDisplayName asset={a}/></button>)}
 <AssetLocationSummary asset={asset}/><AssetInformationCoverage asset={asset} data={data} compact/>
 <section className="explorer-technical"><h3>Thông số — Technical properties</h3>{technical?.length?technical.map(t=><div className="explorer-record" key={t.id}><strong>{t.attribute_label}</strong><p>{t.value_number??t.value_text??"Unavailable"} {t.unit} <StatusBadge>{t.reviewed_provenance!.verification_level}</StatusBadge></p><TechnicalMetadataPopover fields={{"Record UUID":t.id,"Source code":t.reviewed_provenance!.source_code,"Evidence ID":t.reviewed_provenance!.evidence_id,Locator:t.reviewed_provenance!.source_locator,Authority:t.reviewed_provenance!.authority,Reviewer:t.reviewed_provenance!.reviewer,"Reviewed at":t.reviewed_provenance!.reviewed_at,Verification:t.verification_status}}/></div>):<p className="muted">{data.technical===null?"Unavailable":"No reviewed technical preview available."}</p>}</section>
 <AssetEvidenceSummary asset={asset} data={data}/>
 <section className="explorer-documents"><h3>Tài liệu — Documents</h3>{data.documents===null?<p>Unavailable</p>:data.documents.length?data.documents.map(d=><p key={d.id}><Link className="text-link" href={`/documents/${d.id}`}>{d.original_file_name} →</Link></p>):<p>No linked documents.</p>}</section>
 <section><h3>Mô hình 3D — 3D Model</h3>{data.links===null?<p>Unavailable</p>:data.links.length?data.links.map(l=><div key={l.id}><p>Representative mapping only</p><Link className="text-link" href={modelHref(asset,l)}>View 3D →</Link><TechnicalMetadataPopover fields={{"Model UUID":l.model_id,"Object key":l.object_key,"Mapping status":l.verification_status}}/></div>):<p>No linked 3D representation.</p>}</section>
 <Link className="text-link" href={`/assets/${asset.id}?paper=1`}>Thông tin đầy đủ — Asset Detail →</Link></aside>;
}

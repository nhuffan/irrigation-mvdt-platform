import { evidenceDisplayText } from "@/lib/evidence-display";
import { OriginLink as Link } from "@/components/documents/document-link";
import { DocumentLink } from "@/components/documents/document-link";
import { modelHref, reviewedPreview } from "@/lib/explorer-state";
import { hierarchy } from "@/lib/asset-location";
import type { Asset } from "@/types/asset";
import type { ExplorerData } from "@/lib/explorer-data";
import { PanelSection, PanelDisclosure } from "@/components/ui/panel-section";
import { AssetDisplayName, AssetMetadata, TechnicalMetadataPopover, StatusBadge } from "./presentation";
import { AssetLocationSummary } from "./asset-location-summary";
import { AssetInformationCoverage } from "./asset-information-coverage";
import { AssetEvidenceSummary } from "./asset-evidence-summary";
export function ExplorerPanel({asset,assets,data,onSelect}:{asset:Asset;assets:Asset[];data:ExplorerData;onSelect:(asset:Asset)=>void;paper?:boolean}) {
 const technical=reviewedPreview(data);const {ancestors,children}=hierarchy(assets,asset);
 return <aside id="selected-asset-panel" className="explorer-panel" aria-label="Selected asset information" tabIndex={-1}>
 <PanelSection title="Selected asset" actions={<StatusBadge>RS</StatusBadge>}>
 <nav aria-label="Asset hierarchy">{ancestors.map(a=><button className="text-link" key={a.id} onClick={()=>onSelect(a)}><AssetDisplayName asset={a}/></button>)}</nav>
 <h3 className="selected-asset-name"><AssetDisplayName asset={asset}/></h3><p className="asset-code">{asset.category.name}</p><AssetMetadata asset={asset}/>
 {children.length>0 && <div className="component-actions">{children.map(a=><button className="text-link" key={a.id} onClick={()=>onSelect(a)}><AssetDisplayName asset={a}/></button>)}</div>}
 <Link className="button compact-button" href={`/assets/${asset.id}`}>Open Asset Detail →</Link>
 </PanelSection>
 <PanelSection title="Technical preview" description="Reviewed fields for this asset">
 {technical?.length?technical.map(t=><article className="explorer-record" key={t.id}><h4>{evidenceDisplayText(t.attribute_label)}</h4><p className="preview-value">{t.value_number??(t.value_text?evidenceDisplayText(t.value_text):"Unavailable")} {t.unit==="text"?"":t.unit} <StatusBadge>{t.reviewed_provenance!.verification_level}</StatusBadge></p><TechnicalMetadataPopover fields={{"Record UUID":t.id,"Source code":t.reviewed_provenance!.source_code,"Evidence ID":t.reviewed_provenance!.evidence_id,Locator:t.reviewed_provenance!.source_locator,Authority:t.reviewed_provenance!.authority,Verification:t.verification_status}}/></article>):<p className="muted">{data.technical===null?"Unavailable":"No reviewed technical preview available."}</p>}
 </PanelSection>
 <PanelDisclosure title="Location & coverage"><AssetLocationSummary asset={asset}/><AssetInformationCoverage asset={asset} data={data} compact/></PanelDisclosure>
 <PanelDisclosure title="Sources & evidence"><AssetEvidenceSummary asset={asset} data={data}/></PanelDisclosure>
 <PanelSection title="Documents & 3D">
 <div className="resource-group"><h4>Documents</h4>{data.documents===null?<p>Unavailable</p>:data.documents.length?data.documents.map(d=><p key={d.id}><DocumentLink className="text-link" href={`/documents/${d.id}`}>{evidenceDisplayText(d.original_file_name)} →</DocumentLink></p>):<p className="muted">No linked documents.</p>}</div>
 <div className="resource-group"><h4>3D representation</h4>{data.links===null?<p>Unavailable</p>:data.links.length?data.links.map(l=><div key={l.id}><p className="summary-note">Representative mapping only</p><Link className="text-link" href={modelHref(asset,l)}>View 3D →</Link><TechnicalMetadataPopover fields={{"Model UUID":l.model_id,"Object key":l.object_key,"Mapping status":l.verification_status}}/></div>):<p className="muted">No linked 3D representation.</p>}</div>
 </PanelSection></aside>;
}

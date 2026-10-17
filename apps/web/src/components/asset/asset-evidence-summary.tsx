import type { Asset } from "@/types/asset";
import type { ExplorerData } from "@/lib/explorer-data";
import { technicalSources } from "@/lib/asset-coverage";
import { assetLocation } from "@/lib/asset-location";
import { TechnicalMetadataPopover } from "./presentation";
export function AssetEvidenceSummary({asset,data}:{asset:Asset;data:ExplorerData}) {
 const location=assetLocation(asset);
 const verifiedLinks=data.links?.filter(l=>l.verification_status==="VERIFIED");
 const rows=[
 {label:"Technical claims",value:technicalSources(data),fields:Object.fromEntries((data.technical??[]).map((t,i)=>[`Claim ${i+1}`,`${t.attribute_label} · ${t.source?.title??"Source unavailable"} · ${t.reviewed_provenance?.authority??"Authority unavailable"}`]))},
 {label:"Location",value:location.location_status==="REFERENCE_LOCATION"?(location.source?"1 reference source":"Reference source unavailable"):location.location_status==="NO_LOCATION"?"No location evidence":"Bound geometry review",fields:{Source:location.source,Locator:location.locator,"Evidence ID":location.evidence_id,Limitation:location.accuracy_limitation}},
 {label:"Documents",value:data.documents===null?"Unavailable":`${data.documents.length} linked file${data.documents.length===1?"":"s"}`,fields:Object.fromEntries((data.documents??[]).map((d,i)=>[`File ${i+1}`,`${d.source.title} · ${d.original_file_name} · ${d.source.verification_status}`]))},
 {label:"O&M",value:data.events===null?"Unavailable":data.events.length?`${data.events.length} verified events`:"No verified evidence",fields:{Scope:"No verified evidence does not mean no real-world activity occurred."}},
 {label:"3D",value:data.links===null?"Unavailable":data.links.length?`${verifiedLinks!.length} verified representative links / ${data.links.length} links`:"No mapping",fields:Object.fromEntries((data.links??[]).map((l,i)=>[`Mapping ${i+1}`,`${l.object_key} · ${l.verification_status} · Representative mapping only`]))},
 ];
 return <section className="evidence-summary" aria-label="Sources and Evidence"><h3>Sources & Evidence</h3>{rows.map(row=><TechnicalMetadataPopover key={row.label} label={`${row.label} · ${row.value}`} fields={Object.keys(row.fields).length?row.fields:{State:row.value}} />)}<p className="summary-note">Source counts use source identity, not file counts. Authority and verification remain separate.</p></section>;
}

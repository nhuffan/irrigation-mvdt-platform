import Link from "next/link";
import { linkedDocumentCounts, publicEvidenceText } from "@/lib/asset-information";
import { evidenceDisplayText } from "@/lib/evidence-display";
import type { Asset } from "@/types/asset";
import type { ExplorerData } from "@/lib/explorer-data";
import { technicalSources } from "@/lib/asset-coverage";
import { assetLocation } from "@/lib/asset-location";
import { TechnicalMetadataPopover } from "./presentation";
export function AssetEvidenceSummary({asset,data}:{asset:Asset;data:ExplorerData}) {
 const location=assetLocation(asset);
 const documentCounts=linkedDocumentCounts(data.documents);
 const sources=[...new Map((data.technical??[]).filter(t=>t.source_id).map(t=>[t.source_id!,t.source])).entries()];
 const verifiedLinks=data.links?.filter(l=>l.verification_status==="VERIFIED");
 const rows=[
 {label:"Technical claims",value:technicalSources(data),fields:Object.fromEntries((data.technical??[]).map((t,i)=>[`Claim ${i+1}`,`${evidenceDisplayText(t.attribute_label)} · ${t.source?.source_code??t.reviewed_provenance?.source_code??"Source unavailable"} · ${publicEvidenceText(t.reviewed_provenance?.source_locator)} · ${t.reviewed_provenance?.authority??"Authority unavailable"}`]))},
 {label:"Location",value:location.location_status==="REFERENCE_LOCATION"?(location.source?"1 reference source":"Reference source unavailable"):location.location_status==="NO_LOCATION"?"No location evidence":"Bound geometry review",fields:{Source:publicEvidenceText(location.source),Locator:publicEvidenceText(location.locator),"Evidence ID":location.evidence_id,Limitation:publicEvidenceText(location.accuracy_limitation)}},
 {label:"Documents",value:data.documents===null?"Unavailable":`${documentCounts.edges} asset–document links · ${documentCounts.distinctPdfHashes??"unknown"} distinct linked PDF hashes`,fields:Object.fromEntries((data.documents??[]).map((d,i)=>[`File ${i+1}`,`${d.source.source_code} · ${evidenceDisplayText(publicEvidenceText(d.source.title))} · ${publicEvidenceText(d.original_file_name)} · ${d.source.verification_status}`]))},
 {label:"O&M",value:data.events===null?"Unavailable":data.events.length?`${data.events.length} verified events`:"No verified evidence",fields:{Scope:"No verified evidence does not mean no real-world activity occurred."}},
 {label:"3D",value:data.links===null?"Unavailable":data.links.length?`${verifiedLinks!.length} verified representative links / ${data.links.length} links`:"No mapping",fields:Object.fromEntries((data.links??[]).map((l,i)=>[`Mapping ${i+1}`,`${publicEvidenceText(l.object_key)} · ${l.verification_status} · Representative mapping only`]))},
 ];
 return <section className="evidence-summary" aria-label="Sources and Evidence"><h3>Sources & Evidence</h3>{rows.map(row=><TechnicalMetadataPopover key={row.label} label={`${row.label} · ${row.value}`} fields={Object.keys(row.fields).length?row.fields:{State:row.value}} />)}{sources.length>0&&<details className="field-locator"><summary>Direct field sources · {sources.length}</summary><ul>{sources.map(([id,source])=><li key={id}><Link className="text-link" href={`/data-sources/${encodeURIComponent(id)}/documents`}>{source?.source_code??"Source record"} · Open source documents →</Link>{source&&<p>{evidenceDisplayText(publicEvidenceText(source.title))}</p>}</li>)}</ul></details>}<p className="summary-note">Source inventory identities, retained PDF files and asset–document links are different units. Shared documents can link to several assets. Source authority and field verification remain separate.</p></section>;
}

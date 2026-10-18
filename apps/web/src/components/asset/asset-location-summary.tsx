import { publicEvidenceHref, publicEvidenceText } from "@/lib/asset-information";
import type { Asset } from "@/types/asset";
import { assetLocation } from "@/lib/asset-location";
import { locationSourceTitle } from "@/lib/asset-display";
import { TechnicalMetadataPopover } from "./presentation";
import { LocationBadge } from "./location-badge";
export function AssetLocationSummary({asset}:{asset:Asset}) {
 const l=assetLocation(asset);const missing=l.location_status==="NO_LOCATION";
 const sourceHref=publicEvidenceHref(l.source_url);
 const scale=l.accuracy_limitation.match(/1:[\d,]+/)?.[0];
 return <section id="location" aria-label="Asset location"><h3>Location</h3><LocationBadge asset={asset}/>
 {missing?<p>Location unavailable</p>:<><p>{locationSourceTitle(l.source)}</p>{scale&&<p>Map scale · {scale}</p>}<p className="summary-note">{l.location_status==="REFERENCE_LOCATION"?"Map-symbol reference location only. Not surveyed geometry.":"Spatial verification applies to the bound geometry only."}</p>{sourceHref&&<a className="text-link" href={sourceHref} target="_blank" rel="noopener noreferrer">Map source ↗</a>}</>}
 <TechnicalMetadataPopover fields={{"Geometry type":l.geometry_type,CRS:l.crs,"WGS84 coordinates (longitude, latitude)":l.geometry?.type==="Point"?l.geometry.coordinates.join(", "):null,Source:publicEvidenceText(l.source),"Evidence ID":l.evidence_id,Locator:publicEvidenceText(l.locator),Limitation:publicEvidenceText(l.accuracy_limitation),"Verification note":publicEvidenceText(l.verification_note),"Review state":l.review_state}}/>
 </section>;
}

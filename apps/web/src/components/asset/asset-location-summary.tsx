import type { Asset } from "@/types/asset";
import { assetLocation } from "@/lib/asset-location";
import { locationSourceTitle } from "@/lib/asset-display";
import { TechnicalMetadataPopover } from "./presentation";
import { LocationBadge } from "./location-badge";
export function AssetLocationSummary({asset}:{asset:Asset}) {
 const l=assetLocation(asset);const missing=l.location_status==="NO_LOCATION";
 const scale=l.accuracy_limitation.match(/1:[\d,]+/)?.[0];
 return <section aria-label="Asset location"><h3>Vị trí — Location</h3><LocationBadge asset={asset}/>
 {missing?<p>Chưa có vị trí — Location unavailable</p>:<><p>{locationSourceTitle(l.source)}</p>{scale&&<p>Map scale · {scale}</p>}<p className="summary-note">{l.location_status==="REFERENCE_LOCATION"?"Map-symbol reference location only. Not surveyed geometry.":"Spatial verification applies to the bound geometry only."}</p>{l.source_url&&<a className="text-link" href={l.source_url} target="_blank" rel="noopener noreferrer">Nguồn bản đồ — Map source ↗</a>}</>}
 <TechnicalMetadataPopover fields={{"Geometry type":l.geometry_type,CRS:l.crs,"WGS84 coordinates (longitude, latitude)":l.geometry?.type==="Point"?l.geometry.coordinates.join(", "):null,Source:l.source,"Evidence ID":l.evidence_id,Locator:l.locator,Limitation:l.accuracy_limitation,"Verification note":l.verification_note,Reviewer:l.reviewer,"Reviewed at":l.reviewed_at,"Review state":l.review_state}}/>
 </section>;
}

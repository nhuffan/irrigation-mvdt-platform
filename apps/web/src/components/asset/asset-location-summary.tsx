import { publicEvidenceText } from "@/lib/asset-information";
import type { Asset } from "@/types/asset";
import { locationSource } from "@/lib/location-evidence";
import { assetLocation } from "@/lib/asset-location";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { locationSourceTitle } from "@/lib/asset-display";
import { OriginLink } from "@/components/documents/document-link";
import { TechnicalMetadataPopover } from "./presentation";
import { LocationBadge } from "./location-badge";
import styles from "./spatial-coverage.module.css";

function SourceLink({documentId, page, href}: {documentId?:string|null; page?:number|null; href?:string|null}) {
  const source = locationSource({document_id:documentId, physical_page:page, source_url:href});
  if (!source.href) return null;
  const content = <>Open source{source.page ? ` · PDF page ${source.page}` : ""} →</>;
  return source.href.startsWith("/") ? <OriginLink className="text-link" href={source.href}>{content}</OriginLink>
    : <a className="text-link" href={source.href} target="_blank" rel="noopener noreferrer">{content}</a>;
}
export function AssetLocationSummary({asset, anchor=true}:{asset:Asset;anchor?:boolean}) {
  const l=assetLocation(asset), missing=l.location_status==="NO_LOCATION";
  return <section id={anchor ? "location" : undefined} aria-label="Asset location"><h3>Location</h3><LocationBadge asset={asset}/>
    {missing ? <><p>{l.reason ?? "No accepted asset-specific location evidence."}</p>{l.next_action && <p className="summary-note">Next: {l.next_action}</p>}{l.review_state === "UNAVAILABLE" && <p role="status">Location review unavailable; no candidate pin is displayed.</p>}</>
      : <><p>{locationSourceTitle(l.source)}</p><p className={styles.warning}>{l.location_status==="REFERENCE_LOCATION" ? "Reference only — not surveyed geometry" : "Spatial verification applies to the bound geometry only."}</p>
        <p className="summary-note">Accuracy: {l.estimated_accuracy_m == null ? "Unknown" : `±${l.estimated_accuracy_m} m`} · Review: {l.review_state === "AVAILABLE" ? "Accepted" : l.review_state.toLowerCase()}</p>
        <SourceLink documentId={l.document_id} page={l.physical_page} href={l.source_url}/>
        {!!l.candidate_count && <><p className="summary-note">Source comparison: {l.reason ?? "Additional candidates await review. The accepted reference is preserved."}</p>{l.next_action && <p className="summary-note">Next: {l.next_action}</p>}</>}
      </>}
    <TechnicalMetadataPopover fields={{"Geometry type":l.geometry_type,CRS:l.crs,"WGS84 coordinates (longitude, latitude)":!missing&&l.geometry?.type==="Point"?l.geometry.coordinates.join(", "):null,Source:publicEvidenceText(l.source),"Evidence ID":l.evidence_id,Locator:publicEvidenceText(l.locator),"Coordinate basis":l.coordinate_basis ?? "Not reported", "Estimated accuracy":l.estimated_accuracy_m == null ? "Unknown" : `${l.estimated_accuracy_m} m`,Limitation:publicEvidenceText(l.accuracy_limitation),"Verification note":publicEvidenceText(l.verification_note),"Review state":l.review_state,"Reviewer role":l.reviewer_role,"Reviewed at":l.reviewed_at,"Source SHA-256":l.source_sha256}}/>
    {!!l.candidates?.length && <div className={styles.sources}>{l.candidates.map(candidate => <article key={candidate.candidate_id}>
      <h4>{candidate.source_label}</h4><p>{evidenceDisplayText(candidate.source)}</p><SourceLink documentId={candidate.document_id} page={candidate.physical_page} href={candidate.source_url}/>
      <TechnicalMetadataPopover fields={{Locator:candidate.locator,"Coordinate basis":candidate.coordinate_basis,"Source CRS":candidate.source_crs,"Identity basis":candidate.identity_basis,Limitation:candidate.accuracy_limitation,"Review issues":candidate.issues.join(" · ")}}/>
    </article>)}</div>}
  </section>;
}

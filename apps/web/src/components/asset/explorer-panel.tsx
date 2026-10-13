import Link from "next/link";
import { modelHref, reviewedPreview, dataset } from "@/lib/explorer-state";
import { assetLocation, hierarchy } from "@/lib/asset-location";
import type { Asset } from "@/types/asset";
import type { ExplorerData } from "@/lib/explorer-data";
import { LocationBadge } from "./location-badge";

export function ExplorerPanel({ asset, assets, data, onSelect, paper = false }: {
  asset: Asset; assets: Asset[]; data: ExplorerData; onSelect: (asset: Asset) => void; paper?: boolean;
}) {
  const technical = reviewedPreview(data);
  const location = assetLocation(asset);
  const { ancestors, children } = hierarchy(assets, asset);
  const events = data.events ? [...data.events].sort((a,b) => b.event_date.localeCompare(a.event_date)) : null;
  const latest = events?.[0];
  return <aside id="selected-asset-panel" className="panel explorer-panel" aria-label="Selected asset information" tabIndex={-1}>
    <p className="eyebrow">Selected asset · {dataset(asset) === "research" ? "RS" : dataset(asset) === "development" ? "DEV" : "Unclassified"}</p>
    <nav aria-label="Asset hierarchy" className="explorer-actions">
      {ancestors.map(parent => <button className="text-link" key={parent.id} onClick={() => onSelect(parent)}>{parent.asset_code} /</button>)}
      <span>{asset.asset_code}</span>
    </nav>
    <h2>{asset.name}</h2><p>{asset.category.name} · {asset.data_status}</p>
    <p className="muted text-sm">Asset ID: {asset.id}</p>
    {asset.parent_asset_id && !ancestors.length && <Link className="text-link" href={`/assets/${asset.parent_asset_id}`}>View parent asset →</Link>}
    <div className="explorer-actions">{children.map(child => <button className="text-link" key={child.id} onClick={() => onSelect(child)}>Component: {child.name}</button>)}</div>
    <section aria-label="Asset location"><h3>Location</h3><LocationBadge asset={asset} />
      <p className="muted">{location.location_status === "REFERENCE_LOCATION" ? "Navigation / presentation only · Not verified GIS evidence" : location.location_status === "NO_LOCATION" ? "Pending evidence · No asset-specific location" : "Spatial review applies only to the bound geometry; readiness gates remain separate."}</p>
      <dl className="location-details"><dt>Geometry / CRS</dt><dd>{location.geometry_type ?? "Unavailable"} · {location.crs ?? "Unavailable"}</dd>
      {location.geometry?.type === "Point" && <><dt>Latitude / longitude</dt><dd>{location.geometry.coordinates[1]}, {location.geometry.coordinates[0]}</dd></>}
      <dt>Source</dt><dd>{location.source ?? "Pending evidence"}{location.source_url && <><br /><a className="text-link" href={location.source_url} target="_blank" rel="noopener noreferrer">Open location source ↗</a></>}</dd>
      {location.evidence_id && <><dt>Evidence ID</dt><dd>{location.evidence_id}</dd></>}
      {location.locator && <><dt>Locator</dt><dd>{location.locator}</dd></>}
      <dt>Accuracy / limitation</dt><dd>{location.accuracy_limitation}</dd>
      <dt>Verification note</dt><dd>{location.verification_note}</dd>
      <dt>Reviewer</dt><dd>{location.reviewer ?? (location.review_state === "UNAVAILABLE" ? "Unavailable" : "Pending evidence")}{location.reviewed_at ? ` · ${location.reviewed_at}` : ""}</dd></dl>
    </section>
    <section><h3>Technical & provenance</h3>
      {technical?.length ? technical.map(t => <div className="explorer-record" key={t.id}>
        <strong>{t.attribute_label}: {t.value_number ?? t.value_text ?? "Unavailable"} {t.unit}</strong>
        <p>{t.verification_status} · {t.reviewed_provenance!.verification_level}</p>
        <details open={paper}><summary>Source / evidence / review</summary><dl>
          <dt>Source / evidence</dt><dd>{t.reviewed_provenance!.source_code} · {t.reviewed_provenance!.evidence_id}</dd>
          <dt>Locator</dt><dd>{t.reviewed_provenance!.source_locator}</dd>
          <dt>Reviewed authority</dt><dd>{t.reviewed_provenance!.authority}</dd>
          <dt>Reviewer</dt><dd>{t.reviewed_provenance!.reviewer} · {t.reviewed_provenance!.reviewed_at}</dd>
        </dl></details>
      </div>) : <p className="muted">{data.technical === null ? "Unavailable — technical data could not load." : "Pending evidence — no reviewed technical preview available."}</p>}
    </section>
    <section><h3>Current verified condition</h3>
      <p>{data.conditionError ? "Unavailable — could not load" : data.condition ? `${data.condition.condition_status} · ${data.condition.condition_date}` : "Missing — pending evidence"}</p>
      {data.condition?.summary && <p>{data.condition.summary}</p>}
    </section>
    <section><h3>Verified O&M</h3><p>Verified events: {events?.length ?? "Unavailable"}</p>
      <p>Inspection: {events?.filter(e => e.event_type === "INSPECTION").length ?? "Unavailable"} · Repair: {events?.filter(e => e.event_type === "REPAIR").length ?? "Unavailable"} · Maintenance: {events?.filter(e => e.event_type === "MAINTENANCE").length ?? "Unavailable"}</p>
      {latest ? <p>Latest: {latest.event_date} · {latest.title}</p> : <p className="muted">{events === null ? "Unavailable — O&M could not load." : "No verified O&M events available. Candidate records are not verified events; pending evidence."}</p>}
    </section>
    <section><h3>Documents</h3><p>Linked documents: {data.documents?.length ?? "Unavailable"}</p>
      {data.documents?.length === 0 && <p className="muted">No linked document available for this asset.</p>}
      <div className="explorer-actions">{data.documents?.map(d => <div key={d.id}><p className="muted text-sm">{d.source.source_code} · {d.source.verification_status}</p><Link className="text-link" href={`/documents/${d.id}`}>Open / preview {d.document_code} →</Link></div>)}</div>
    </section>
    <section><h3>3D representation</h3><p>Model links: {data.links?.length ?? "Unavailable"}</p>
      {data.links?.map(l => <div className="explorer-record" key={l.id}><p>Mapped object: {l.object_name ?? l.object_key} · {l.verification_status}</p><p className="muted text-sm">Object key: {l.object_key}</p><Link className="text-link" href={modelHref(asset,l)}>View 3D →</Link></div>)}
      {!!data.links?.length && <p className="muted text-sm">Representative mapping only; no surveyed placement or complete semantic coverage is implied.</p>}
      {data.links?.length === 0 && <p className="muted">No 3D representation linked.</p>}
    </section>
    <Link className="text-link" href={`/assets/${asset.id}`}>View Detail →</Link>
  </aside>;
}

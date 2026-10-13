import { modelHref, reviewedPreview } from "@/lib/explorer-state";
import Link from "next/link";
import type { Asset } from "@/types/asset";
import type { ExplorerData } from "@/lib/explorer-data";
export function ExplorerPanel({ asset, data }: { asset: Asset; data: ExplorerData }) {
  const technical = reviewedPreview(data);
  return <aside className="panel explorer-panel" aria-label="Selected asset information">
    <p className="eyebrow">Selected asset · {asset.asset_code.startsWith("RS-") ? "RS" : asset.asset_code.startsWith("DEV-") ? "DEV" : "Unclassified"}</p>
    <h2>{asset.name}</h2><p>{asset.asset_code} · {asset.category.name}</p>
    <p>{asset.data_status} · {asset.geometry ? asset.geometry.type : "Geometry unavailable"}</p>
    <p className="muted text-sm">Asset ID: {asset.id}</p>
    {asset.parent_asset_id && <Link className="text-link" href={`/assets/${asset.parent_asset_id}`}>View parent asset</Link>}
    <h3>Technical & provenance</h3>
    {technical?.length ? technical.map(t => <div className="explorer-record" key={t.id}>
      <strong>{t.attribute_label}: {t.value_number ?? t.value_text ?? "Unavailable"} {t.unit}</strong>
      <p>{t.verification_status} · {t.reviewed_provenance!.verification_level}</p>
      <dl><dt>Source / evidence</dt><dd>{t.reviewed_provenance!.source_code} · {t.reviewed_provenance!.evidence_id}</dd>
      <dt>Locator</dt><dd>{t.reviewed_provenance!.source_locator}</dd>
      <dt>Reviewed authority</dt><dd>{t.reviewed_provenance!.authority}</dd></dl>
    </div>) : <p className="muted">{data.technical === null ? "Technical data unavailable — could not load." : "No reviewed technical preview available."}</p>}
    <h3>O&M / condition</h3><p>Current condition: {data.conditionError ? "Unavailable — could not load" : data.condition?.condition_status ?? "Unavailable"}</p>
    <p>Verified events: {data.events?.length ?? "Unavailable"}</p>
    {data.events?.length === 0 && <p className="muted">No verified O&M events available. Candidate records are not verified events.</p>}
    <h3>Digital links</h3><p>Documents: {data.documents?.length ?? "Unavailable"} · 3D links: {data.links?.length ?? "Unavailable"}</p>
    <div className="explorer-actions"><Link className="text-link" href={`/assets/${asset.id}`}>View Detail →</Link>
    {data.documents?.map(d => <Link className="text-link" key={d.id} href={`/documents/${d.id}`}>Open Document · {d.document_code}</Link>)}
    {data.links?.map(l => <Link className="text-link" key={l.id} href={modelHref(asset, l)}>View 3D · {l.verification_status} →</Link>)}</div>
    {!!data.links?.length && <p className="muted text-sm">A linked representation does not establish surveyed geometry or full asset coverage.</p>}
  </aside>;
}

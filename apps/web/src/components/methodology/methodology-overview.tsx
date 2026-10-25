import { OriginLink } from "@/components/documents/document-link";
import { PanelSection, MetricCard } from "@/components/ui/panel-section";
import type { getResearchSummary } from "@/lib/research-summary";
import { RESERVOIR_HREF } from "@/lib/site-scope";
import styles from "./methodology-overview.module.css";

type Summary = Awaited<ReturnType<typeof getResearchSummary>>;
const value = (count: number | null) => count ?? "Unavailable";

export function MethodologyOverview({ summary }: { summary: Summary }) {
  const { rows, totals } = summary;
  const asset = rows.find(row => !row.parent_id && row.direct_l2 !== null && row.direct_l2 > 0) ?? rows[0];
  const source = summary.sources.find(item => item.id && item.link_available && item.live_document_records !== null && item.live_document_records > 0);
  const unknownLocations = rows.some(row => !["REFERENCE_LOCATION", "VERIFIED_GEOMETRY", "NO_LOCATION"].includes(row.location));
  const referenceCount = unknownLocations ? null : totals.reference_points;
  const eventNote = totals.verified_om === null ? "Event readback unavailable" : totals.verified_om === 0 ? "No verified event evidence" : "Verified dated records only";
  const missingLocations = rows.filter(row => row.location === "NO_LOCATION").length;
  const verifiedLocations = rows.filter(row => row.location === "VERIFIED_GEOMETRY").length;
  const locationNote = unknownLocations ? "Location coverage unavailable" : `${missingLocations} without location · ${verifiedLocations} verified geometry`;
  const linkCount = rows.some(row => row.links === null) ? null : rows.reduce((sum, row) => sum + (row.links ?? 0), 0);
  const cards = [
    { label: "Asset registry", body: "Stable identities and parent–component scope.", href: `${RESERVOIR_HREF}#assets`, action: "Open Registry" },
    { label: "GIS context", body: "Asset references in geographic context; gaps stay visible.", href: `${RESERVOIR_HREF}#asset-gis`, action: "Open Asset GIS" },
    { label: "Representative 3D", body: "Linked model objects connect representation to an asset.", href: `${RESERVOIR_HREF}/3d`, action: "Open 3D" },
    { label: "Technical & O&M records", body: "Reviewed source values and dated records retain their provenance.", href: asset ? `/assets/${asset.id}` : null, action: "Open Asset Detail" },
    { label: "Source documents", body: "Retained originals and page locators make claims traceable.", href: source ? `/data-sources/${source.id}/documents` : null, action: "Open Documents" },
    { label: "AI Research", body: "Scoped retrieval returns evidence and original references.", href: "/ai-research-preview", action: "Open AI Research" },
  ];
  return <div className={styles.overview}>
    <section id="methodology-framework"><PanelSection title="Level-1 information framework" description="One asset identity connects the registry, spatial context, representation, records and original evidence.">
      <div className={styles.framework}>{cards.map(card => <article key={card.label}>
        <h3>{card.label}</h3><p>{card.body}</p>
        {card.href ? <OriginLink href={card.href} returnAnchor="methodology-framework">{card.action} →</OriginLink> : <span className="muted">{card.action}: unavailable</span>}
      </article>)}</div>
    </PanelSection></section>
    <section id="methodology-evidence"><PanelSection title="Live evidence snapshot" description="Read-only API observations from the managed reservoir; counts describe available records, not research validation.">
      <div className={styles.metrics}>
        <MetricCard label="Research assets" value={totals.all} note={`${totals.primary} primary · ${totals.components} components`} />
        <MetricCard label="Reviewed L2 records" value={value(totals.all_l2)} note="Source-reported / historical" />
        <MetricCard label="Distinct linked PDFs" value={value(summary.unique_linked_documents)} note="Metadata hashes; retained bytes require original checks" />
        <MetricCard label="Verified O&M events" value={value(totals.verified_om)} note={eventNote} />
        <MetricCard label="Reference locations" value={value(referenceCount)} note={locationNote} />
        <MetricCard label="Representative 3D links" value={value(linkCount)} note="Representation, not surveyed geometry" />
      </div>
      <p className={styles.readback}>Current readback: <time dateTime={summary.read_at}>{summary.read_at}</time>. Missing responses remain unavailable. Parent and component evidence is reported separately.</p>
    </PanelSection></section>
    <PanelSection title="Contribution & research boundary">
      <div className={styles.boundary}>
        <div><h3>What the prototype demonstrates</h3><p><strong>Phase 1 prototype: software complete.</strong> A traceable Level-1 information model: navigate from an asset to its reviewed records, representative geometry and source evidence, with scoped retrieval as an experimental extension.</p></div>
        <div><h3>What the evidence does not establish</h3><p>Source-reported history and reference locations do not certify present condition, geometric accuracy or operational decisions. RAG Lite retrieves evidence; it does not generate advice.</p></div>
      </div>
      <p className={styles.acceptance}>{summary.workflow.status === "AVAILABLE" ? <><strong>Research acceptance: {summary.workflow.data.research_status === "COMPLETE" ? "Complete" : "Pending"}.</strong> {summary.workflow.data.compiler_status} · {summary.workflow.data.dataset_status}. Detailed reviews and study gates are available below.</> : <><strong>Research acceptance: unavailable.</strong> The current evidence gates could not be read; no historical status has been substituted.</>}</p>
    </PanelSection>
  </div>;
}

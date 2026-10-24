import { OriginLink as Link } from "@/components/documents/document-link";
import type { Asset } from "@/types/asset";
import type { ExplorerData } from "@/lib/explorer-data";
import { assetLocation } from "@/lib/asset-location";
import { descendantIds, l2Count, type TechnicalRecords } from "@/lib/asset-hierarchy";
import { linkedDocumentCounts } from "@/lib/asset-information";
import { AssetDisplayName } from "./presentation";

export function AssetDataAvailability({ asset, assets, records, data }: {
  asset: Asset; assets: Asset[] | null; records: TechnicalRecords; data: ExplorerData;
}) {
  const descendants = assets === null ? null : descendantIds(assets, asset.id);
  const direct = l2Count([asset.id], records);
  const descendantL2 = descendants === null ? null : l2Count(descendants, records);
  const documents = linkedDocumentCounts(data.documents);
  const sourceIds = data.technical === null ? null : new Set(data.technical.flatMap(t => t.source_id ? [t.source_id] : []));
  const location = assetLocation(asset);
  const show = (value: number | null) => value ?? "Unavailable";
  return <section className="panel mt-6" id="data-availability" aria-label="Data availability and limitations">
    <h2>Data availability &amp; limitations</h2>
    <dl className="detail-list">
      <div><dt>Reviewed L2</dt><dd>{show(direct)} direct · {show(descendantL2)} descendant</dd></div>
      <div><dt>Direct technical source identities</dt><dd>{sourceIds === null ? "Unavailable" : sourceIds.size}</dd></div>
      <div><dt>Methodology</dt><dd><Link className="text-link" href={`/methodology#methodology-asset-${asset.asset_code}`}>Asset applicability &amp; coverage metrics →</Link></dd></div>
      <div><dt>Asset–document links</dt><dd>{show(documents.edges)}</dd></div>
      <div><dt>Distinct linked PDF hashes</dt><dd>{show(documents.distinctPdfHashes)}{documents.unhashablePdfs ? ` · ${documents.unhashablePdfs} PDF hash(es) unavailable` : ""}</dd></div>
    </dl>
    {descendants?.length ? <>
      <p className="summary-note">This parent groups {descendants.length} components. Their technical records remain with each component and are not copied into this asset. Zero direct L2 is not an applicable-field completeness denominator.</p>
      <ul>{assets!.filter(a => descendants.includes(a.id)).map(a => <li key={a.id}><Link className="text-link" href={`/assets/${a.id}#technical`}><AssetDisplayName asset={a}/></Link> · {show(l2Count([a.id], records))} direct L2</li>)}</ul>
    </> : <p className="summary-note">Direct records describe this asset only. Availability counts are not MAIM completeness scores; applicable requirements and missingness are reported separately.</p>}
    {descendants === null && <p className="summary-note">Hierarchy readback is unavailable; descendant coverage is unknown.</p>}
    <p className="summary-note">Source inventory entries, physically retained PDFs and asset–document links are different units. The counts above describe this asset&apos;s direct records and links; shared PDF hashes must not be summed across assets. A document metadata record alone does not prove retained bytes. {data.documents?.length === 0 && "No asset-linked files does not imply that its cited source has no document."} <Link className="text-link" href="/methodology#coverage">Study source and document coverage →</Link></p>
    <p className="summary-note">{location.location_status === "REFERENCE_LOCATION" ? "Location is a reviewed navigation reference, not surveyed asset geometry." : location.location_status === "VERIFIED_GEOMETRY" ? "Spatial review applies only to its bound geometry and evidence." : "No reviewed asset location is available."} {asset.geometry === null ? "Canonical asset geometry is absent." : asset.geometry === undefined ? "Canonical geometry availability is unknown." : "Canonical geometry presence alone is not an accuracy certificate."}</p>
    <p className="summary-note">{data.events === null ? "Verified O&M availability is unknown because the API readback failed." : data.events.length ? `${data.events.length} verified O&M event(s) are linked; historical events do not establish present condition.` : "No verified O&M event is available. This does not mean no inspection, repair or maintenance occurred."}</p>
    <p className="summary-note">{data.links === null ? "3D association readback is unavailable." : data.links.length ? `${data.links.length} representative 3D link(s); coordinate mode is reported in the 3D section. A parent representative model does not identify a child building or certify surveyed placement.` : asset.parent_asset_id ? "No established 3D link exists for this asset. A parent's representative LOCAL model does not verify this child or supply its placement." : "No established 3D link exists for this asset. No surveyed 3D placement is inferred."}</p>
  </section>;
}

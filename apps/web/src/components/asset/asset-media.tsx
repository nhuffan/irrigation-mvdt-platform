import { TechnicalMetadataPopover } from "./presentation";
import Link from "next/link";
import { getAssetDocuments, getAssetModelLinks, getModels } from "@/lib/api";
import { DocumentList } from "@/components/documents/document-list";
import { VerificationBadge } from "./source-info";
import { SectionError } from "./section-error";
export async function AssetMedia({
  assetId,
  reservoirId,
}: {
  assetId: string;
  reservoirId: string;
}) {
  const [documents, links, models] = await Promise.allSettled([
    getAssetDocuments(assetId),
    getAssetModelLinks(assetId),
    getModels(reservoirId),
  ]);
  return (
    <>
      <section className="panel mt-6">
        <h2>Documents</h2>
        {documents.status === "fulfilled" ? (
          <DocumentList documents={documents.value} />
        ) : (
          <SectionError title="Documents" />
        )}
      </section>
      <section className="panel mt-6">
        <h2>3D representation</h2>
        {links.status !== "fulfilled" || models.status !== "fulfilled" ? (
          <SectionError title="3D representation" />
        ) : links.value.length ? (
          <ul className="document-list">
            {links.value.map((link) => (
              <li key={link.id}>
                <p>
                  {models.value.find((m) => m.id === link.model_id)?.name ??
                    "Model"}{" "}
                  · Representative object
                </p>
                <p>Representative mapping only</p><TechnicalMetadataPopover fields={{"Model UUID":link.model_id,"Asset UUID":link.asset_id,"Object key":link.object_key,Verification:link.verification_status}}/><VerificationBadge status={link.verification_status} />
                <Link
                  className="text-link"
                  href={`/reservoirs/${reservoirId}/3d?model=${link.model_id}&object=${encodeURIComponent(link.object_key)}`}
                >
                  View in 3D →
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted mt-3">
            No 3D representation is linked to this asset.
          </p>
        )}
        <Link
          className="text-link mt-4"
          href={`/reservoirs/${reservoirId}#asset-gis`}
        >
          View on GIS →
        </Link>
      </section>
    </>
  );
}

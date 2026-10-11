import { Suspense } from "react";
import { AssetMedia } from "./asset-media";
import { AssetOm } from "./asset-om";
import Link from "next/link";
import { getAsset, getReservoir } from "@/lib/api";
import type { Asset } from "@/types/asset";
import { AssetMap } from "@/components/map/asset-map";
import { AssetStatus } from "./asset-status";
export async function AssetDetail({ asset }: { asset: Asset }) {
  const [reservoir, parent] = await Promise.all([
    getReservoir(asset.reservoir_id),
    asset.parent_asset_id
      ? getAsset(asset.parent_asset_id)
      : Promise.resolve(null),
  ]);
  return (
    <>
      <div className="registry-grid">
        <section className="panel">
          <p className="eyebrow">Asset identity</p>
          <h2>Classification & hierarchy</h2>
          <dl className="detail-list">
            <div>
              <dt>Reservoir</dt>
              <dd>
                <Link
                  className="text-link"
                  href={`/reservoirs/${reservoir.id}`}
                >
                  {reservoir.name} · {reservoir.code}
                </Link>
              </dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>
                {asset.category.name} · {asset.category.code}
              </dd>
            </div>
            <div>
              <dt>Parent asset</dt>
              <dd>
                {parent ? (
                  <Link className="text-link" href={`/assets/${parent.id}`}>
                    {parent.name} · {parent.asset_code}
                  </Link>
                ) : (
                  "No parent asset"
                )}
              </dd>
            </div>
            <div>
              <dt>Asset UUID</dt>
              <dd className="break-all text-sm">{asset.id}</dd>
            </div>
          </dl>
        </section>
        <section className="panel">
          <p className="eyebrow">Information readiness</p>
          <h2>Data readiness</h2>
          <dl className="detail-list">
            <div>
              <dt>Data status</dt>
              <dd>
                <AssetStatus status={asset.data_status} />
              </dd>
            </div>
            <div>
              <dt>Description</dt>
              <dd className="muted">
                {asset.description ?? "No description recorded."}
              </dd>
            </div>
          </dl>
        </section>
      </div>
      <section className="panel mt-6">
        <p className="eyebrow">Technical information</p>
        <h2>Technical description</h2>
        <p className="muted mt-3 whitespace-pre-wrap">
          {asset.technical_description ??
            "Technical information has not been recorded."}
        </p>
      </section>
      <Suspense
        fallback={
          <section className="panel mt-6" role="status">
            Loading technical information and O&M histories…
          </section>
        }
      >
        <AssetOm assetId={asset.id} />
      </Suspense>
      <Suspense fallback={<p role="status">Loading documents and 3D links…</p>}>
        <AssetMedia assetId={asset.id} reservoirId={asset.reservoir_id} />
      </Suspense>
      <section className="mt-10">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Spatial information</p>
            <h2>{asset.geometry?.type ?? "Spatial geometry: Not available in this dataset"}</h2>
          </div>
          {asset.geometry && <span className="muted text-sm">WGS 84 · EPSG:4326</span>}
        </div>
        <AssetMap reservoir={reservoir} assets={[asset]} />
      </section>
    </>
  );
}

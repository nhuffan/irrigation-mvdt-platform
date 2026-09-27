import Link from "next/link";
import type { Asset } from "@/types/asset";
import { AssetStatus } from "./asset-status";
export function AssetRegistry({ assets }: { assets: Asset[] }) {
  if (assets.length === 0)
    return (
      <div className="panel">
        <h3 className="font-semibold">No assets registered</h3>
        <p className="muted mt-2">
          No verified assets are currently available for this reservoir.
        </p>
      </div>
    );
  return (
    <div className="asset-table-wrap">
      <table className="asset-table">
        <caption className="sr-only">Reservoir asset registry</caption>
        <thead>
          <tr>
            <th scope="col">Asset</th>
            <th scope="col">Category</th>
            <th scope="col">Data status</th>
            <th scope="col">Geometry</th>
            <th scope="col">Parent</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((asset) => {
            const parent = assets.find(
              (item) => item.id === asset.parent_asset_id,
            );
            return (
              <tr key={asset.id}>
                <th scope="row">
                  <Link className="text-link" href={`/assets/${asset.id}`}>
                    {asset.name}
                  </Link>
                  <span className="asset-code">{asset.asset_code}</span>
                </th>
                <td>{asset.category.name}</td>
                <td>
                  <AssetStatus status={asset.data_status} />
                </td>
                <td>{asset.geometry?.type ?? "Not recorded"}</td>
                <td>
                  {asset.parent_asset_id ? (
                    <Link
                      className="text-link"
                      href={`/assets/${asset.parent_asset_id}`}
                    >
                      {parent?.asset_code ?? "View parent"}
                    </Link>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

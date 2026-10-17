import { getExplorerData } from "@/lib/explorer-data";
import { getReservoirAssets } from "@/lib/api";
import type { Reservoir } from "@/types/reservoir";
import { AssetExplorer } from "./asset-explorer";
export async function ReservoirAssets({ reservoir }: { reservoir: Reservoir }) {
  const assets = await getReservoirAssets(reservoir.id);
  const records = Object.fromEntries(await Promise.all(assets.map(async a => [a.id, await getExplorerData(a.id)])));
  return (
    <section id="assets" className="mt-10">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Asset inventory</p>
          <h2>Assets</h2>
        </div>
        <span className="muted">{assets.length} research assets</span>
      </div>
      <AssetExplorer reservoir={reservoir} assets={assets} records={records} />
    </section>
  );
}

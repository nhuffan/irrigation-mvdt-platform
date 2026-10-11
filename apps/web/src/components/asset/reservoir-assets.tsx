import { getReservoirAssets } from "@/lib/api";
import type { Reservoir } from "@/types/reservoir";
import { AssetExplorer } from "./asset-explorer";
export async function ReservoirAssets({ reservoir }: { reservoir: Reservoir }) {
  const assets = await getReservoirAssets(reservoir.id);
  return (
    <section id="assets" className="mt-10">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Asset inventory</p>
          <h2>Assets</h2>
        </div>
        <span className="muted">{assets.length} records</span>
      </div>
      <AssetExplorer reservoir={reservoir} assets={assets} />
    </section>
  );
}

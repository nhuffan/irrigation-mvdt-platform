import { getReservoirAssets } from "@/lib/api";
import type { Reservoir } from "@/types/reservoir";
import { AssetMap } from "@/components/map/asset-map";
import { AssetRegistry } from "./asset-registry";
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
      <AssetMap reservoir={reservoir} assets={assets} />
      <div className="mt-6">
        <AssetRegistry assets={assets} />
      </div>
    </section>
  );
}

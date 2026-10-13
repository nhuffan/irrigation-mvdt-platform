import { notFound } from "next/navigation";
import { ApiError, getAsset, getReservoir } from "@/lib/api";
import { ReservoirAssets } from "@/components/asset/reservoir-assets";
import { getReservoirs } from "@/lib/api";
import { ReservoirMap } from "@/components/map/reservoir-map";
export const dynamic = "force-dynamic";
export default async function MapPage({ searchParams }: { searchParams: Promise<{ asset?: string }> }) {
  const { asset } = await searchParams;
  if (asset) {
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(asset)) notFound();
    const selected = await getAsset(asset).catch(error => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    });
    const reservoir = await getReservoir(selected.reservoir_id);
    return <main className="page-shell"><p className="eyebrow">Interactive asset GIS</p><h1>{reservoir.name}</h1><ReservoirAssets reservoir={reservoir} /></main>;
  }
  const reservoirs = await getReservoirs();
  return (
    <main className="map-shell">
      <div className="map-heading">
        <div>
          <p className="eyebrow">Spatial explorer</p>
          <h1>Reservoir GIS map</h1>
        </div>
        <p className="muted">
          {reservoirs.length} reservoirs · Select a marker to explore
        </p>
      </div>
      <ReservoirMap reservoirs={reservoirs} />
    </main>
  );
}

import { getReservoirs } from "@/lib/api";
import { ReservoirMap } from "@/components/map/reservoir-map";
export const dynamic = "force-dynamic";
export default async function MapPage() {
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

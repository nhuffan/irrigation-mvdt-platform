import { notFound } from "next/navigation";
import { ApiError, getAsset, getReservoir, getReservoirAssets } from "@/lib/api";
import { ObservationMap } from "@/components/map/observation-map";
import { MANAGED_RESERVOIR_ID } from "@/lib/site-scope";
import { ReservoirAssets } from "@/components/asset/reservoir-assets";
export const dynamic = "force-dynamic";
export default async function MapPage({ searchParams }: { searchParams: Promise<{ asset?: string }> }) {
  const { asset } = await searchParams;
  if (asset) {
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(asset)) notFound();
    await getAsset(asset).catch(error => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    });
  }
  const reservoir = await getReservoir(MANAGED_RESERVOIR_ID);
  const observationAssets = await getReservoirAssets(reservoir.id);
  return <main className="map-shell"><p className="eyebrow">Asset GIS</p><h1>{reservoir.name}</h1><ReservoirAssets reservoir={reservoir} /><ObservationMap reservoir={reservoir} assets={observationAssets} /></main>;
}

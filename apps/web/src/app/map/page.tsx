import { notFound, redirect } from "next/navigation";
import { ApiError, getAsset, getReservoir, getReservoirAssets } from "@/lib/api";
import { publicAssets } from "@/lib/public-client-data";
import { PageHeader } from "@/components/ui/page-header";
import { ObservationMap } from "@/components/map/observation-map";
import { MANAGED_RESERVOIR_ID } from "@/lib/site-scope";

export const dynamic = "force-dynamic";

export default async function MapPage({ searchParams }: {
  searchParams: Promise<{ asset?: string; paper?: string }>;
}) {
  const { asset, paper } = await searchParams;
  if (asset) {
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(asset)) notFound();
    const selected = await getAsset(asset).catch(error => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    });
    redirect(`/reservoirs/${selected.reservoir_id}?asset=${encodeURIComponent(selected.id)}${paper === "1" ? "&paper=1" : ""}#asset-gis`);
  }
  const reservoir = await getReservoir(MANAGED_RESERVOIR_ID);
  const assets = await getReservoirAssets(reservoir.id);
  return <main className="map-shell">
    <PageHeader eyebrow="Spatial context" title="GIS Map" description="An observation map for satellite and irrigation context. Basemap imagery and reference markers support navigation; they do not verify asset geometry or current condition." />
    <ObservationMap reservoir={reservoir} assets={publicAssets(assets)} />
  </main>;
}

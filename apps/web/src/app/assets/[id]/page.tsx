import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getAsset } from "@/lib/api";
import { AssetDetail } from "@/components/asset/asset-detail";
export const dynamic = "force-dynamic";
export default async function AssetPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
  )
    notFound();
  // Resolve existence before streaming so a missing asset returns a real HTTP 404.
  const asset = await getAsset(id).catch((error) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });
  return (
    <main className="page-shell">
      <Link
        className="text-link"
        href={`/reservoirs/${asset.reservoir_id}#assets`}
      >
        ← Back to reservoir assets
      </Link>
      <div className="page-heading mt-8">
        <div>
          <p className="eyebrow">Asset detail · {asset.asset_code}</p>
          <h1>{asset.name}</h1>
        </div>
      </div>
      <Suspense
        fallback={
          <section className="panel" role="status">
            Loading asset information…
          </section>
        }
      >
        <AssetDetail asset={asset} />
      </Suspense>
    </main>
  );
}

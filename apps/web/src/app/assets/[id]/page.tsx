import { AssetDisplayName } from "@/components/asset/presentation";
import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getAsset } from "@/lib/api";
import { AssetDetail } from "@/components/asset/asset-detail";
export const dynamic = "force-dynamic";
export default async function AssetPage({
  params, searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{paper?:string}>;
}) {
  const { id } = await params;
  const paper=(await searchParams).paper==="1";
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
    <main className={paper?"page-shell clean-paper":"page-shell"}>
      <Link
        className="text-link"
        href={`/reservoirs/${asset.reservoir_id}#assets`}
      >
        ← Back to reservoir assets
      </Link>
      <div className="page-heading mt-8">
        <div>
          <p className="eyebrow">Asset detail</p>
          <h1><AssetDisplayName asset={asset}/></h1>
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

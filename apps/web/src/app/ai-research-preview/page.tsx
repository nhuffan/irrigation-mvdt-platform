import { parseEvidenceSearch } from "@/lib/evidence-search-state";
import { AskPanel } from "@/components/rag-lite/ask-panel";
import { getReservoirAssets } from "@/lib/api";
import { MANAGED_RESERVOIR_ID } from "@/lib/site-scope";
import styles from "@/components/rag-lite/rag-lite.module.css";

export const dynamic = "force-dynamic";

export default async function AiResearchPreview({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  let enabled = false;
  let available = true;
  const base = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  try {
    const response = await fetch(`${base}/experimental/rag-lite/status`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
    if (!response.ok) throw new Error("Unavailable");
    enabled = (await response.json()).enabled === true;
  } catch { available = false; }
  const assets = enabled ? await getReservoirAssets(MANAGED_RESERVOIR_ID).catch(() => []) : [];
  const demos = enabled ? await Promise.all(assets.map(async asset => {
    try {
      const response = await fetch(`${base}/experimental/rag-lite/demo-questions?asset_id=${asset.id}&reservoir_id=${MANAGED_RESERVOIR_ID}`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
      return response.ok && (await response.json()).length > 0 ? asset.id : null;
    } catch { return null; }
  })) : [];
  const initialSearch = parseEvidenceSearch(await searchParams, assets.map(asset => asset.id));
  return <main className={`page-shell ${styles.page}`}>
    <header className={styles.intro}><h1>AI Research</h1></header>
    <p role="note" className={styles.notice}>Experimental historical evidence · Human verification required. Not current condition or operational advice.</p>
    {enabled ? <AskPanel initialSearch={initialSearch} initialAssetId={demos.find(id => id !== null) ?? undefined} assets={assets.map(({ id, asset_code, name, parent_asset_id }) => ({ id, asset_code, name, parent_asset_id }))} /> : <p role="status" className="panel">
      {available ? "Experimental evidence search is disabled. The core application remains available." : "Evidence search is unavailable. Retry when the local services are running."}
    </p>}
  </main>;
}

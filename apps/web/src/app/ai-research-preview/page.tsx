import { RetryView } from "@/components/ui/retry-view";
import { parseEvidenceSearch } from "@/lib/evidence-search-state";
import { AskPanel } from "@/components/rag-lite/ask-panel";
import { getReservoirAssets } from "@/lib/api";
import { MANAGED_RESERVOIR_ID } from "@/lib/site-scope";
import styles from "@/components/rag-lite/rag-lite.module.css";

export const dynamic = "force-dynamic";

export default async function AiResearchPreview({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  let enabled = false;
  let available = true;
  let generationAvailable = false;
  const base = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  try {
    const response = await fetch(`${base}/experimental/rag-lite/status?reservoir_id=${encodeURIComponent(MANAGED_RESERVOIR_ID)}`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
    if (!response.ok) throw new Error("Unavailable");
    const status = await response.json();
    enabled = status.enabled === true;
    generationAvailable = status.generation_available === true;
  } catch { available = false; }
  let assetsUnavailable = false;
  const assets = enabled ? await getReservoirAssets(MANAGED_RESERVOIR_ID).catch(() => { assetsUnavailable = true; return []; }) : [];
  const initialSearch = parseEvidenceSearch(await searchParams, assets.map(asset => asset.id));
  return <main className={`page-shell ${styles.page}`}>
    <header className={styles.intro}><h1>AI Research</h1></header>
    <p role="note" className={styles.notice}>Experimental research · Historical or reference evidence · Human verification required. No current-condition assessment or engineering advice.</p>
    {enabled && !assetsUnavailable && assets.length > 0 ? <AskPanel key={initialSearch ? JSON.stringify(initialSearch) : "clean"} generationAvailable={generationAvailable} initialSearch={initialSearch} initialAssetId={assets.find(asset => !asset.parent_asset_id)?.id} assets={assets.map(({ id, asset_code, name, parent_asset_id }) => ({ id, asset_code, name, parent_asset_id }))} /> : <section role="status" className="panel">
      {enabled && !assetsUnavailable && !assets.length ? "No research assets are registered for this reservoir." : assetsUnavailable ? "The asset list could not be loaded. Availability has not been replaced with zero." : available ? "Experimental evidence search is disabled. The core application remains available." : "Evidence search is unavailable. Retry when the local services are running."}
      {(!available || assetsUnavailable) && <RetryView/>}
    </section>}
  </main>;
}

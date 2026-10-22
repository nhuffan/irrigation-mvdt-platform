import Link from "next/link";
import { AskPanel } from "@/components/rag-lite/ask-panel";
import { getReservoirAssets } from "@/lib/api";
import { MANAGED_RESERVOIR_ID, RESERVOIR_HREF } from "@/lib/site-scope";
import styles from "@/components/rag-lite/rag-lite.module.css";

export const dynamic = "force-dynamic";

export default async function AiResearchPreview() {
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
  return <main className={`page-shell ${styles.page}`}>
    <div className={styles.topline}><Link className="text-link" href={RESERVOIR_HREF}>← Back to reservoir</Link></div>
    <header className={styles.intro}><p className="eyebrow">RAG Lite — Experimental Evidence Search</p><h1>Find the evidence behind a value.</h1><p>Search historical technical fields and original document passages linked to your asset.</p></header>
    <p role="note" className={styles.notice}>Experimental historical documentary retrieval. Not current condition or operational advice. Human verification required.</p>
    {enabled ? <AskPanel initialAssetId={demos.find(id => id !== null) ?? undefined} assets={assets.map(({ id, asset_code, name, parent_asset_id }) => ({ id, asset_code, name, parent_asset_id }))} /> : <p role="status" className="panel">
      {available ? "Experimental evidence search is disabled. The core application remains available." : "Evidence search is unavailable. Retry when the local services are running."}
    </p>}
  </main>;
}

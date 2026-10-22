import Link from "next/link";
import { AskPanel } from "@/components/rag-lite/ask-panel";
import { getReservoirAssets } from "@/lib/api";
import { MANAGED_RESERVOIR_ID, RESERVOIR_HREF } from "@/lib/site-scope";

export const dynamic = "force-dynamic";

export default async function AiResearchPreview() {
  let enabled = false;
  let available = true;
  try {
    const base = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(`${base}/experimental/rag-lite/status`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
    if (!response.ok) throw new Error("Unavailable");
    enabled = (await response.json()).enabled === true;
  } catch { available = false; }
  const assets = enabled ? await getReservoirAssets(MANAGED_RESERVOIR_ID).catch(() => []) : [];
  return <main className="page-shell">
    <Link className="text-link" href={RESERVOIR_HREF}>← Reservoir</Link>
    <div className="page-heading mt-6"><div>
      <p className="eyebrow">EXPERIMENTAL / FUTURE WORK</p>
      <h1>AI Research Preview</h1>
      <p className="muted mt-3">Historical asset information and original document passage search.</p>
    </div></div>
    <p role="note" className="rounded-lg border border-amber-300 bg-amber-50 p-4 mb-6">
      Experimental future work — human verification required. Retrieval-only demonstration.
      Historical records do not establish current condition or support operating decisions.
    </p>
    {enabled ? <AskPanel assets={assets.map(({ id, asset_code, name, parent_asset_id }) => ({ id, asset_code, name, parent_asset_id }))} /> : <p role="status" className="panel p-6">
      {available ? "Experimental preview is disabled. The core application remains available." : "The data API is unavailable. Retry when the local services are running."}
    </p>}
  </main>;
}

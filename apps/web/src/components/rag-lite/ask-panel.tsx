"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Asset } from "@/types/asset";
import { assetDisplayName } from "@/lib/asset-display";
import { evidenceDisplayText } from "@/lib/evidence-display";

type Citation = {
  citation_id: string; kind: string; source_id: string; source_code: string;
  document_id: string | null; record_id: string | null; page: number | null;
  locator: string; asset_id: string | null; url: string; content_url: string | null;
  title: string; excerpt: string; attribute_key: string | null; value_number: number | null;
  value_text: string | null; unit: string | null; evidence_id: string | null;
  source_date: string | null; record_status: string | null; source_status: string;
  authority: string | null;
};
type Result = { status: string; answer: string | null; citations: Citation[]; limitations: string[] };
type Demo = { question: string; attribute_key: string };

export function AskPanel({ assets }: { assets: Pick<Asset, "id" | "asset_code" | "name" | "parent_asset_id">[] }) {
  const [assetId, setAssetId] = useState(assets[0]?.id ?? "");
  const [allDocs, setAllDocs] = useState(false);
  const [question, setQuestion] = useState("");
  const [queryType, setQueryType] = useState("auto");
  const [mode, setMode] = useState("evidence_only");
  const [demos, setDemos] = useState<Demo[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  useEffect(() => {
    if (!assetId || allDocs) return;
    const controller = new AbortController();
    fetch(`/api/rag-lite?asset_id=${encodeURIComponent(assetId)}`, { signal: controller.signal })
      .then(r => r.ok ? r.json() : []).then(value => { if (!controller.signal.aborted) setDemos(value); })
      .catch(() => {});
    return () => controller.abort();
  }, [assetId, allDocs]);
  function reset() {
    active.current?.abort(); setBusy(false); setResult(null); setError(""); setDemos([]);
  }
  async function ask(value = question, attributeKey?: string) {
    active.current?.abort();
    const controller = new AbortController(); active.current = controller;
    setBusy(true); setError(""); setResult(null);
    try {
      const response = await fetch("/api/rag-lite", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: value, asset_id: allDocs ? null : assetId,
          all_authorized_docs: allDocs, mode, query_type: attributeKey ? "attribute" : allDocs ? "document" : queryType,
          ...(attributeKey ? { attribute_key: attributeKey } : {}), top_k: 5 }),
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]),
      });
      if (!response.ok) throw new Error(response.status === 429 ? "Request limit reached. Wait a minute and retry." : "Search unavailable. Check the feature flag, scope and local API.");
      const received: Result = await response.json();
      if (!controller.signal.aborted) setResult(received);
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Search unavailable");
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <div className="grid gap-6 lg:grid-cols-[2fr_3fr]">
    <aside className="panel p-6 self-start">
      <h2>Search scope</h2>
      <form className="mt-4 grid gap-4" onSubmit={e => { e.preventDefault(); void ask(); }}>
        <label className="grid gap-2">Asset or component
          <select className="border rounded p-2 w-full" disabled={allDocs || busy} value={assetId} onChange={e => { reset(); setAssetId(e.target.value); }}>
            {assets.map(asset => <option key={asset.id} value={asset.id}>{asset.parent_asset_id ? "Component: " : "Primary: "}{assetDisplayName(asset)}</option>)}
          </select>
        </label>
        <label className="flex gap-2 items-start"><input type="checkbox" checked={allDocs} disabled={busy} onChange={e => { reset(); setAllDocs(e.target.checked); }} />Search all authorized documents in this reservoir</label>
        <p className="muted text-sm">Asset searches use direct reviewed links only. Parent and child evidence is kept separate.</p>
        {!allDocs && <label className="grid gap-2">Search type
          <select className="border rounded p-2" value={queryType} disabled={busy} onChange={e => setQueryType(e.target.value)}>
            <option value="auto">SQL first, then document passages</option><option value="attribute">Historical attributes</option><option value="document">Document passages</option>
          </select>
        </label>}
        <label className="grid gap-2">Question or keywords
          <textarea className="border rounded p-2" rows={4} value={question} maxLength={1000} minLength={2} required disabled={busy} onChange={e => setQuestion(e.target.value)} placeholder="Enter an attribute key or source-language document keywords" />
        </label>
        <label className="grid gap-2">Response mode
          <select className="border rounded p-2" value={mode} disabled={busy} onChange={e => setMode(e.target.value)}>
            <option value="evidence_only">Evidence only</option><option value="grounded_answer">Grounded answer (provider unavailable)</option>
          </select>
        </label>
        <button className="button" type="submit" disabled={busy || (!allDocs && !assetId) || question.trim().length < 2}>{busy ? "Searching…" : "Find evidence"}</button>
      </form>
      {demos.length > 0 && !allDocs && <div className="mt-6"><h3>Try an existing field</h3><div className="grid gap-2 mt-2">{demos.map(demo => <button key={demo.attribute_key} className="text-link text-left break-words" disabled={busy} onClick={() => { setQuestion(demo.question); void ask(demo.question, demo.attribute_key); }}>{demo.attribute_key.replaceAll("_", " ")}</button>)}</div></div>}
    </aside>
    <section aria-live="polite" aria-busy={busy} className="min-w-0">
      {error && <p role="alert" className="panel p-6">{error}</p>}
      {!result && !error && <div className="panel p-6"><h2>Evidence</h2><p className="muted mt-3">Choose an exact asset or explicit corpus-wide search. Results link to original records and retained PDFs. Keyword retrieval has no semantic or translation model.</p></div>}
      {result && <>
        <h2>{result.status.replaceAll("_", " ")}</h2>
        {result.answer && <p className="panel p-4 mt-3 whitespace-pre-wrap">{result.answer.split(/(\[[^\]]+\])/g).map((part, i) => {
          const citation = result.citations.find(c => part === `[${c.citation_id}]`);
          return citation ? <a key={i} className="text-link" href={`#${citation.citation_id}`}>[{result.citations.indexOf(citation) + 1}]</a> : part;
        })}</p>}
        {!result.citations.length && <p className="panel p-6 mt-3">No supporting evidence was found for this request.</p>}
        <div className="grid gap-4 mt-4">{result.citations.map(c => <article key={c.citation_id} id={c.citation_id} className="panel p-5 break-words">
          <p className="eyebrow">HISTORICAL / REFERENCE · {c.record_status ?? "DOCUMENT EXCERPT"}</p>
          <h3 className="font-semibold">{evidenceDisplayText(c.title)}</h3>
          <p className="mt-3 whitespace-pre-wrap">{c.kind === "technical_attribute" ? `${c.attribute_key}: ${c.value_number ?? (c.value_text ? evidenceDisplayText(c.value_text) : "Unknown")} ${c.unit === "text" ? "" : c.unit ?? ""}` : c.excerpt}</p>
          <p className="muted text-sm mt-3">{c.source_code} · {c.locator} · Source date: {c.source_date ?? "Unknown"}<br />Source status: {c.source_status} · Authority: {c.authority ?? "Unknown"}{c.evidence_id && <> · {c.evidence_id}</>}</p>
          <div className="flex flex-wrap gap-4 mt-3"><Link className="text-link" href={c.url}>Open {c.document_id ? "document" : "asset record"}</Link><Link className="text-link" href={`/data-sources/${c.source_id}/documents`}>Source</Link>{c.content_url && <a className="text-link" href={c.content_url}>Original PDF · page {c.page}</a>}</div>
          <details className="mt-3 text-xs muted"><summary>Citation ID and scope</summary><p>{c.citation_id}</p><p>Asset UUID: {c.asset_id ?? "Corpus-wide; no asset attribution"}</p></details>
        </article>)}</div>
        <ul className="muted text-sm list-disc pl-5 mt-5">{result.limitations.map((line, i) => <li key={i}>{line}</li>)}</ul>
      </>}
    </section>
  </div>;
}

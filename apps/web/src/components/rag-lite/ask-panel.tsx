"use client";

import { useEffect, useRef, useState } from "react";
import type { Asset } from "@/types/asset";
import { assetDisplayName } from "@/lib/asset-display";
import { evidenceDisplayText } from "@/lib/evidence-display";
import type { RagCoverage, RagDemo, RagResult } from "@/lib/rag-lite";
import { SearchCoverage } from "./search-coverage";
import { EvidenceResults } from "./evidence-results";
import styles from "./rag-lite.module.css";

type SearchAsset = Pick<Asset, "id" | "asset_code" | "name" | "parent_asset_id">;
type SearchRun = { result: RagResult; scopeName: string };

export function AskPanel({ assets, initialAssetId }: { assets: SearchAsset[]; initialAssetId?: string }) {
  const [assetId, setAssetId] = useState(initialAssetId ?? assets[0]?.id ?? "");
  const [allDocs, setAllDocs] = useState(false);
  const [question, setQuestion] = useState("");
  const [queryType, setQueryType] = useState("auto");
  const [demos, setDemos] = useState<RagDemo[]>([]);
  const [coverage, setCoverage] = useState<RagCoverage | null>(null);
  const [coverageError, setCoverageError] = useState(false);
  const [coverageAttempt, setCoverageAttempt] = useState(0);
  const [run, setRun] = useState<SearchRun | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const active = useRef<AbortController | null>(null);
  const heading = useRef<HTMLHeadingElement | null>(null);
  const errorHeading = useRef<HTMLDivElement | null>(null);
  const input = useRef<HTMLInputElement | null>(null);
  const lastRequest = useRef<{ question: string; attributeKey?: string } | null>(null);

  useEffect(() => () => active.current?.abort(), []);
  useEffect(() => { if (run) heading.current?.focus({ preventScroll: true }); }, [run]);
  useEffect(() => { if (error) errorHeading.current?.focus(); }, [error]);
  useEffect(() => {
    const controller = new AbortController();
    if (!allDocs && !assetId) return;
    const url = `/api/rag-lite?coverage=true${allDocs ? "" : `&asset_id=${encodeURIComponent(assetId)}`}`;
    fetch(url, { signal: controller.signal, cache: "no-store" })
      .then(async r => {
        if (!r.ok) throw new Error("Coverage unavailable");
        const value: RagCoverage = await r.json();
        if (!controller.signal.aborted) { setCoverage(value); setCoverageError(false); }
      }).catch(() => { if (!controller.signal.aborted) { setCoverage(null); setCoverageError(true); } });
    return () => controller.abort();
  }, [assetId, allDocs, coverageAttempt]);
  useEffect(() => {
    if (!assetId || allDocs) return;
    const controller = new AbortController();
    fetch(`/api/rag-lite?asset_id=${encodeURIComponent(assetId)}`, { signal: controller.signal, cache: "no-store" })
      .then(r => r.ok ? r.json() : []).then(value => { if (!controller.signal.aborted) setDemos(value); })
      .catch(() => {});
    return () => controller.abort();
  }, [assetId, allDocs]);

  function reset(clearDemos = false) {
    active.current?.abort(); setBusy(false); setRun(null); setError(""); lastRequest.current = null;
    if (clearDemos) { setDemos([]); setCoverage(null); setCoverageError(false); }
  }
  function clear() { reset(); setQuestion(""); input.current?.focus(); }
  function cancel() { active.current?.abort(); setBusy(false); input.current?.focus(); }
  async function ask(value = question, attributeKey?: string) {
    const trimmed = value.trim();
    if (trimmed.length < 2 || (!allDocs && !assetId)) return;
    active.current?.abort();
    const controller = new AbortController(); active.current = controller;
    lastRequest.current = { question: trimmed, attributeKey };
    setQuestion(trimmed); setBusy(true); setError(""); setRun(null);
    const selected = assets.find(a => a.id === assetId);
    const scopeName = allDocs ? "all authorized PDFs · no asset attribution" : selected ? assetDisplayName(selected) : "selected asset";
    try {
      const response = await fetch("/api/rag-lite", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed, asset_id: allDocs ? null : assetId,
          all_authorized_docs: allDocs, mode: "evidence_only", query_type: attributeKey ? "attribute" : allDocs ? "document" : queryType,
          ...(attributeKey ? { attribute_key: attributeKey } : {}), top_k: 5 }),
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]),
      });
      if (!response.ok) throw new Error(response.status === 429 ? "Search limit reached. Wait a minute, then retry." : response.status === 404 ? "This experimental search is currently disabled." : "Search could not be completed. Check the local connection and retry.");
      const result: RagResult = await response.json();
      if (!controller.signal.aborted) setRun({ result, scopeName });
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Search could not be completed. Please retry.");
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }

  const currentCoverage = coverage && (allDocs ? !coverage.diagnostics : coverage.diagnostics?.asset_id === assetId) ? coverage : null;
  function searchCorpus() { reset(true); setAllDocs(true); input.current?.focus(); }

  return <section className={`panel ${styles.searchPanel}`} aria-label="Evidence search">

      <form onSubmit={e => { e.preventDefault(); void ask(); }}>
        <fieldset className={styles.scope} disabled={busy}>
          <legend>Search in</legend>
          <label><input type="radio" name="evidence-scope" checked={!allDocs} onChange={() => { reset(true); setAllDocs(false); }} />Selected asset</label>
          <label><input type="radio" name="evidence-scope" checked={allDocs} onChange={() => { reset(true); setAllDocs(true); }} />All authorized PDFs</label>
        </fieldset>
        <div className={`${styles.searchRow} ${allDocs ? styles.corpusRow : ""}`}>
          {!allDocs && <label className={styles.field}>Asset or component
            <select disabled={busy} value={assetId} onChange={e => { reset(true); setAssetId(e.target.value); }}>
              {assets.map(asset => <option key={asset.id} value={asset.id}>{asset.parent_asset_id ? "Component: " : ""}{assetDisplayName(asset)}</option>)}
            </select>
          </label>}
          <label className={styles.field}>Question or document keywords
            <input ref={input} type="search" value={question} minLength={2} maxLength={1000} required autoComplete="off" disabled={busy}
              onChange={e => { reset(); setQuestion(e.target.value); }} placeholder="Search historical values or original document keywords" />
          </label>
          <button className={`button ${styles.submit}`} type="submit" disabled={busy || question.trim().length < 2 || (!allDocs && !assetId)}>{busy ? "Searching…" : "Search evidence"}<span aria-hidden="true">↗</span></button>
        </div>
        {allDocs && <p className={styles.scopeNotice}>Corpus-wide · not attributed to any asset.</p>}
        <div className={styles.searchToolbar}>
          <div className={styles.tools}>
            <details className={styles.options}>
              <summary>Search options</summary>
              <div className={styles.optionBody}>
                {!allDocs && <label className={styles.field}>Search mode
                  <select disabled={busy} value={queryType} onChange={e => { reset(); setQueryType(e.target.value); }}>
                    <option value="auto">Technical fields, then PDF passages</option><option value="attribute">Technical fields only</option><option value="document">Document passages only</option>
                  </select>
                </label>}
                <SearchCoverage coverage={currentCoverage} allDocs={allDocs} unavailable={coverageError || (!allDocs && !assetId)}
                  onRetry={() => { setCoverageError(false); setCoverageAttempt(value => value + 1); }} />
              </div>
            </details>
            {demos.length > 0 && !allDocs && <details className={styles.suggestions}>
              <summary>Suggested questions</summary>
              <div>{demos.slice(0, 3).map(demo => <button type="button" key={demo.attribute_key} disabled={busy} onClick={() => void ask(demo.question, demo.attribute_key)}>{evidenceDisplayText(demo.attribute_label ?? demo.attribute_key.replaceAll("_", " "))}</button>)}</div>
            </details>}
          </div>
          <div className={styles.searchActions}>
            {busy ? <button type="button" className="text-link" onClick={cancel}>Cancel</button> : question && <button type="button" className="text-link" onClick={clear}>Clear</button>}
          </div>
        </div>
      </form>
    <div aria-live="polite" aria-atomic="true" className={styles.srOnly}>{busy ? "Searching historical evidence" : run ? `${run.result.citations.length} ${run.result.citations.length === 1 ? "reference" : "references"} returned for ${run.scopeName}` : ""}</div>
    <div className={styles.outcome}>
      {busy && <p className={styles.progress} role="status">Searching…</p>}
      {error && <div ref={errorHeading} tabIndex={-1} role="alert" className={styles.error}>
        <h2>Search unavailable</h2><p>{error}</p><button className="text-link" onClick={() => void ask(lastRequest.current?.question ?? question, lastRequest.current?.attributeKey)}>Retry search</button>
      </div>}
      {run && <EvidenceResults result={run.result} headingRef={heading} onCorpus={!allDocs ? searchCorpus : undefined} />}
      {!busy && !run && !error && <p className={styles.startState}>Enter keywords to search historical evidence.</p>}
    </div>
  </section>;
}

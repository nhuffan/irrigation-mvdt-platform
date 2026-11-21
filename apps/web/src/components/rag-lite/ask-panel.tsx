"use client";

import { useEffect, useEffectEvent, useRef, useState } from "react";
import type { Asset } from "@/types/asset";
import { assetDisplayName } from "@/lib/asset-display";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { GUARDRAIL_QUESTIONS, type RagCoverage, type RagDemo, type RagResult, type RagSearchMode } from "@/lib/rag-lite";
import { evidenceAssetGroups, evidenceQueryPayload, evidenceSearchUrl, evidenceSearchFromUrl, evidenceRequestError, type EvidenceSearchState } from "@/lib/evidence-search-state";
import { SearchCoverage } from "./search-coverage";
import { EvidenceResults } from "./evidence-results";
import styles from "./rag-lite.module.css";

type SearchAsset = Pick<Asset, "id" | "asset_code" | "name" | "parent_asset_id">;
type SearchRun = { result: RagResult; scopeName: string; pageChange: boolean; mode: RagSearchMode };
type SearchOptions = {
  value?: string; attributeKey?: string; page?: number; pageChange?: boolean;
  requestedType?: string; restored?: EvidenceSearchState; mode?: RagSearchMode;
};

export function AskPanel({ assets, generationAvailable, initialAssetId, initialSearch }: { assets: SearchAsset[]; generationAvailable: boolean; initialAssetId?: string; initialSearch?: EvidenceSearchState | null }) {
  const [assetId, setAssetId] = useState(initialSearch?.assetId || initialAssetId || assets[0]?.id || "");
  const [allDocs, setAllDocs] = useState(initialSearch?.allDocs ?? false);
  const [question, setQuestion] = useState(initialSearch?.question ?? "");
  const [queryType, setQueryType] = useState<string>(initialSearch?.queryType ?? "auto");
  const [selectedMode, setSelectedMode] = useState<RagSearchMode>("evidence_only");
  const mode = generationAvailable ? selectedMode : "evidence_only";
  const [demos, setDemos] = useState<RagDemo[]>([]);
  const [coverage, setCoverage] = useState<RagCoverage | null>(null);
  const [coverageError, setCoverageError] = useState(false);
  const [coverageAttempt, setCoverageAttempt] = useState(0);
  const [run, setRun] = useState<SearchRun | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const completedRequest = useRef<EvidenceSearchState | null>(null);
  const active = useRef<AbortController | null>(null);
  const heading = useRef<HTMLHeadingElement | null>(null);
  const errorHeading = useRef<HTMLDivElement | null>(null);
  const input = useRef<HTMLInputElement | null>(null);
  const lastRequest = useRef<SearchOptions | null>(null);

  const restoreSearch = useEffectEvent(() => {
    const stored = evidenceSearchFromUrl(window.location.href, assets.map(asset => asset.id));
    active.current?.abort(); setRun(null); if (!stored || stored.assetId !== assetId || stored.allDocs !== allDocs) { setDemos([]); setCoverage(null); setCoverageError(false); } setError(""); setCancelled(false); completedRequest.current = null; lastRequest.current = null;
    setSelectedMode("evidence_only");
    if (!stored) { setBusy(false); setAssetId(initialAssetId || assets[0]?.id || ""); setAllDocs(false); setQuestion(""); setQueryType("auto"); return; }
    setAssetId(stored.assetId || initialAssetId || assets[0]?.id || ""); setAllDocs(stored.allDocs);
    setQuestion(stored.question); setQueryType(stored.queryType);
    if (stored.draft) { setBusy(false); return; }
    // History restores supporting evidence. A model call always requires a fresh user action.
    void ask({ value: stored.question, attributeKey: stored.attributeKey, page: stored.page, requestedType: stored.queryType, restored: stored });
  });
  useEffect(() => {
    const gate = new AbortController();
    // StrictMode's first effect is cleaned before this microtask can submit.
    queueMicrotask(() => { if (!gate.signal.aborted) restoreSearch(); });
    const onPop = () => restoreSearch(); window.addEventListener("popstate", onPop);
    return () => { gate.abort(); active.current?.abort(); window.removeEventListener("popstate", onPop); };
  }, []);
  useEffect(() => {
    if (run) {
      const anchor = window.location.hash.slice(1);
      const target = run.result.citations.some(c => c.citation_id === anchor) ? document.getElementById(anchor) : null;
      (target ?? heading.current)?.focus({ preventScroll: true });
      if (target || run.pageChange) (target ?? heading.current)?.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [run]);
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

  function remember(state: EvidenceSearchState | null) {
    window.history.replaceState(null, "", evidenceSearchUrl(window.location.href, state));
  }
  function reset(clearDemos = false) {
    remember(null);
    active.current?.abort(); setBusy(false); setRun(null); setError(""); setCancelled(false); lastRequest.current = null; completedRequest.current = null;
    if (clearDemos) { setDemos([]); setCoverage(null); setCoverageError(false); }
  }
  function draft(patch: Partial<EvidenceSearchState>, scopeChange = false) {
    reset(scopeChange);
    const next = { assetId, allDocs, question, queryType: queryType as EvidenceSearchState["queryType"], page: 1, ...patch, draft: true };
    if (next.allDocs) { next.assetId = ""; next.queryType = "document"; }
    remember(next);
  }
  function clear() { draft({ question: "" }); setQuestion(""); input.current?.focus(); }
  function cancel() { active.current?.abort(); remember(run ? completedRequest.current : { assetId: allDocs ? "" : assetId, allDocs, question, queryType: allDocs ? "document" : queryType as EvidenceSearchState["queryType"], page: 1, draft: true }); setBusy(false); setCancelled(true); input.current?.focus(); }
  async function ask({ value = question, attributeKey, page = 1, pageChange = false, requestedType = queryType, restored, mode: requestedMode = "evidence_only" }: SearchOptions = {}) {
    const trimmed = value.trim(), selectedId = restored?.assetId ?? assetId, corpus = restored?.allDocs ?? allDocs;
    if (trimmed.length < 2 || (!corpus && !selectedId)) return;
    active.current?.abort();
    const controller = new AbortController(); active.current = controller;
    const requestMode = generationAvailable ? requestedMode : "evidence_only";
    const resolvedType = attributeKey ? "attribute" : corpus ? "document" : requestedType === "attribute" || requestedType === "document" ? requestedType : "auto";
    lastRequest.current = { value: trimmed, attributeKey, page, requestedType: resolvedType, mode: requestMode };
    const requestState: EvidenceSearchState = { question: trimmed, assetId: corpus ? "" : selectedId, allDocs: corpus, queryType: resolvedType, attributeKey, page };
    remember(requestState);
    setQuestion(trimmed); setBusy(true); setError(""); setCancelled(false);
    if (!pageChange) setRun(null);
    const selected = assets.find(a => a.id === selectedId);
    const scopeName = corpus ? "all authorized PDFs · no asset attribution" : selected ? assetDisplayName(selected) : "selected asset";
    try {
      const response = await fetch("/api/rag-lite", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(evidenceQueryPayload(requestState, requestMode)),
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]),
      });
      if (!response.ok) throw new Error(evidenceRequestError(response.status));
      const result: RagResult = await response.json();
      if (!controller.signal.aborted) {
        const completed = { ...requestState, page: result.pagination?.page ?? page };
        completedRequest.current = completed; remember(completed);
        setRun({ result, scopeName, pageChange, mode: requestMode });
      }
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error && e.name === "TimeoutError" ? "Search timed out. Check the local connection and retry." : e instanceof Error ? e.message : "Search could not be completed. Please retry.");
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }

  const currentCoverage = coverage && (allDocs ? !coverage.diagnostics : coverage.diagnostics?.asset_id === assetId) ? coverage : null;
  function searchCorpus() { draft({ allDocs: true }, true); setAllDocs(true); input.current?.focus(); }
  const grounded = mode === "grounded_answer";
  const submitLabel = grounded ? "Get grounded answer" : "Search evidence";
  const pendingLabel = grounded ? "Preparing grounded answer…" : run ? "Loading the requested page…" : "Searching historical evidence…";

  return <section className={`panel ${styles.searchPanel}`} aria-label="Evidence search">

      <form onSubmit={e => { e.preventDefault(); if (!busy) void ask({ mode }); }}>
        <fieldset className={styles.scope}>
          <legend>Search in</legend>
          <label><input type="radio" name="evidence-scope" checked={!allDocs} onChange={() => { draft({ allDocs: false, assetId }, true); setAllDocs(false); }} />Selected asset</label>
          <label><input type="radio" name="evidence-scope" checked={allDocs} onChange={() => { draft({ allDocs: true }, true); setAllDocs(true); }} />All authorized PDFs</label>
        </fieldset>
        {generationAvailable && <fieldset className={styles.scope} disabled={busy}>
          <legend>Result type</legend>
          <label><input type="radio" name="result-type" checked={!grounded} onChange={() => { draft({}); setSelectedMode("evidence_only"); }} />Evidence only</label>
          <label><input type="radio" name="result-type" checked={grounded} onChange={() => { draft({}); setSelectedMode("grounded_answer"); }} />Grounded answer</label>
        </fieldset>}
        <div className={`${styles.searchRow} ${allDocs ? styles.corpusRow : ""}`}>
          {!allDocs && <label className={styles.field}>Asset or component
            <select value={assetId} onChange={e => { draft({ assetId: e.target.value }, true); setAssetId(e.target.value); }}>
              {evidenceAssetGroups(assets).map(({ parent, children }) => children.length ? <optgroup key={parent.id} label={assetDisplayName(parent)}>
                <option value={parent.id}>{assetDisplayName(parent)} (parent only)</option>
                {children.map(asset => <option key={asset.id} value={asset.id}>↳ {assetDisplayName(asset)}</option>)}
              </optgroup> : <option key={parent.id} value={parent.id}>{assetDisplayName(parent)}</option>)}
            </select>
          </label>}
          <label className={styles.field}>Question or document keywords
            <input ref={input} type="search" value={question} minLength={2} maxLength={1000} required autoComplete="off"
              onChange={e => { draft({ question: e.target.value }); setQuestion(e.target.value); }} placeholder="Search historical values or original document keywords" />
          </label>
          <button className={`button ${styles.submit}`} type="submit" disabled={busy || question.trim().length < 2 || (!allDocs && !assetId)}>{busy ? "Working…" : submitLabel}<span aria-hidden="true">↗</span></button>
        </div>
        <p className="scope-context">{allDocs ? "Corpus-wide · not attributed to any asset." : assets.find(a => a.id === assetId) ? assetDisplayName(assets.find(a => a.id === assetId)!) : "Select an asset or component"}</p>
        <p className={styles.readiness} role="status" aria-label="Evidence availability">
          {currentCoverage ? <>
            {!allDocs && <span>{currentCoverage.diagnostics?.reviewed_attributes ?? 0} reviewed fields</span>}
            <span>{currentCoverage.searchable_documents} searchable PDFs</span>
            {currentCoverage.image_only_documents > 0 && <span>{currentCoverage.image_only_documents} image-only</span>}
            {currentCoverage.unavailable_documents > 0 && <span>{currentCoverage.unavailable_documents} unavailable</span>}
            {!!currentCoverage.diagnostics?.unscoped_documents && <span>{currentCoverage.diagnostics.unscoped_documents} without reviewed passages</span>}
            {!!currentCoverage.diagnostics?.not_authorized_documents && <span>{currentCoverage.diagnostics.not_authorized_documents} not authorized</span>}
          </> : coverageError ? "Evidence availability unknown · retry in Search options" : "Checking evidence availability…"}
        </p>
        <div className={styles.searchToolbar}>
          <div className={styles.tools}>
            <details className={styles.options}>
              <summary>Search options</summary>
              <div className={styles.optionBody}>
                {!allDocs && <label className={styles.field}>Search mode
                  <select value={queryType} onChange={e => { draft({ queryType: e.target.value as EvidenceSearchState["queryType"] }); setQueryType(e.target.value); }}>
                    <option value="auto">Technical fields, then PDF passages</option><option value="attribute">Technical fields only</option><option value="document">Document passages only</option>
                  </select>
                </label>}
                <SearchCoverage coverage={currentCoverage} allDocs={allDocs} unavailable={coverageError || (!allDocs && !assetId)}
                  onRetry={() => { setCoverageError(false); setCoverageAttempt(value => value + 1); }} />
              </div>
            </details>
            {demos.length > 0 && !allDocs && <details className={styles.suggestions}>
              <summary>Suggested questions</summary>
              <div>{demos.map(demo => <button type="button" key={`${demo.query_type ?? "attribute"}:${demo.question}`} disabled={busy} onClick={() => { setQueryType(demo.query_type ?? "attribute"); void ask({ value: demo.question, attributeKey: demo.attribute_key ?? undefined, requestedType: demo.query_type ?? "attribute", mode }); }}>{demo.query_type === "document" ? "PDF · " : ""}{evidenceDisplayText(demo.attribute_label ?? demo.question)}</button>)}</div>
            </details>}
            {generationAvailable && !allDocs && <details className={styles.suggestions}>
              <summary>Try the guardrails</summary>
              <div>{GUARDRAIL_QUESTIONS.map(text => <button type="button" key={text} disabled={busy} onClick={() => { setSelectedMode("grounded_answer"); setQueryType("auto"); void ask({ value: text, requestedType: "auto", mode: "grounded_answer" }); }}>{text}</button>)}</div>
            </details>}
          </div>
          <div className={styles.searchActions}>
            {busy ? <button type="button" className="text-link" onClick={cancel}>Cancel</button> : question && <button type="button" className="text-link" onClick={clear}>Clear</button>}
          </div>
        </div>
      </form>
    <div aria-live="polite" aria-atomic="true" className={styles.srOnly}>{busy ? pendingLabel : run ? `${run.result.citations.length} ${run.result.citations.length === 1 ? "reference" : "references"} returned for ${run.scopeName}` : ""}</div>
    <div className={styles.outcome} aria-busy={busy}>
      {busy && <p className={styles.progress}>{pendingLabel}</p>}
      {cancelled && <p className={styles.progress} role="status">Search cancelled. Your keywords are kept.</p>}
      {error && <div ref={errorHeading} tabIndex={-1} role="alert" className={styles.error}>
        <h2>{grounded ? "Grounded answer unavailable" : "Search unavailable"}</h2><p>{error}</p><button className="text-link" onClick={() => void ask(lastRequest.current ?? undefined)}>Retry {grounded ? "answer" : "search"}</button>
      </div>}
      {run && <EvidenceResults result={run.result} mode={run.mode} headingRef={heading} onCorpus={!allDocs ? searchCorpus : undefined}
        onPage={page => void ask({ ...lastRequest.current, page, pageChange: true, mode: "evidence_only" })} />}
      {!busy && !run && !error && !cancelled && <p className={styles.startState}>Enter keywords to search historical evidence.</p>}
    </div>
  </section>;
}

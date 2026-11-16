import type { RagSearchMode } from "./rag-lite";

/** Persist only a validated search request. Results are always rechecked against live evidence. */
export type EvidenceSearchState = {
  assetId: string; allDocs: boolean; question: string;
  queryType: "auto" | "attribute" | "document"; attributeKey?: string; page: number; draft?: boolean;
};
const keys = ["q", "scope", "asset", "search", "field", "page", "draft"];

export function parseEvidenceSearch(params: Record<string, string | string[] | undefined>, assetIds: string[]): EvidenceSearchState | null {
  if (keys.some(key => Array.isArray(params[key]))) return null;
  const value = (key: string) => typeof params[key] === "string" ? params[key] as string : "";
  const draft = value("draft") === "1";
  if (value("draft") && !draft) return null;
  const question = value("q").trim(), scope = value("scope"), assetId = value("asset");
  const queryType = value("search"), attributeKey = value("field");
  const pageText = value("page") || "1", page = Number(pageText);
  if ((!draft && question.length < 2) || question.length > 1000 || !["asset", "corpus"].includes(scope)) return null;
  if (scope === "asset" ? !assetIds.includes(assetId) : !!assetId) return null;
  if (queryType !== "auto" && queryType !== "attribute" && queryType !== "document") return null;
  if (scope === "corpus" && (queryType !== "document" || attributeKey)) return null;
  if (attributeKey && (queryType !== "attribute" || !/^[a-zA-Z0-9_]{1,100}$/.test(attributeKey))) return null;
  if (!/^[1-9]\d{0,4}$/.test(pageText) || !Number.isSafeInteger(page) || page > 10000) return null;
  return { assetId, allDocs: scope === "corpus", question, queryType, ...(draft ? { draft: true } : {}), ...(attributeKey ? { attributeKey } : {}), page };
}

export function evidenceSearchUrl(href: string, state: EvidenceSearchState | null): string {
  const url = new URL(href, "http://local.invalid");
  for (const key of keys) url.searchParams.delete(key);
  if (state) {
    url.searchParams.set("q", state.question);
    if (state.draft) url.searchParams.set("draft", "1");
    url.searchParams.set("scope", state.allDocs ? "corpus" : "asset");
    if (!state.allDocs) url.searchParams.set("asset", state.assetId);
    url.searchParams.set("search", state.queryType);
    if (state.attributeKey) url.searchParams.set("field", state.attributeKey);
    url.searchParams.set("page", String(state.page));
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

export function evidenceQueryPayload(state: EvidenceSearchState, mode: RagSearchMode = "evidence_only") {
  return {
    question: state.question,
    asset_id: state.allDocs ? null : state.assetId,
    all_authorized_docs: state.allDocs,
    mode,
    query_type: state.queryType,
    ...(state.attributeKey ? { attribute_key: state.attributeKey } : {}),
    ...(mode === "grounded_answer" ? { top_k: 5 } : { page: state.page, page_size: 5 }),
  };
}

type HierarchyAsset = { id: string; parent_asset_id: string | null };
/** Retain exact UUID selection while grouping the existing small hierarchy. */
export function evidenceAssetGroups<T extends HierarchyAsset>(assets: T[]): { parent: T; children: T[] }[] {
  const ids = new Set(assets.map(asset => asset.id));
  const roots = assets.filter(asset => !asset.parent_asset_id || !ids.has(asset.parent_asset_id));
  const groups = roots.map(parent => ({ parent, children: assets.filter(asset => asset.parent_asset_id === parent.id) }));
  const included = new Set(groups.flatMap(group => [group.parent.id, ...group.children.map(asset => asset.id)]));
  // Malformed/deeper hierarchies stay selectable; no implicit scope inheritance.
  return [...groups, ...assets.filter(asset => !included.has(asset.id)).map(parent => ({ parent, children: [] as T[] }))];
}

/** Back/Forward reads the current URL, including duplicate-parameter rejection. */
export function evidenceSearchFromUrl(href: string, assetIds: string[]): EvidenceSearchState | null {
  const url = new URL(href, "http://local.invalid"), params: Record<string, string | string[]> = {};
  for (const key of url.searchParams.keys()) {
    const values = url.searchParams.getAll(key); params[key] = values.length === 1 ? values[0] : values;
  }
  return parseEvidenceSearch(params, assetIds);
}

export function evidenceRequestError(status: number): string {
  return status === 429 ? "Search limit reached. Wait a minute, then retry."
    : status === 404 ? "This experimental search is currently disabled."
    : status === 504 ? "The request timed out. Check the local connection and retry."
    : "Search could not be completed. Check the local connection and retry.";
}

/** Persist only a validated search request. Results are always rechecked against live evidence. */
export type EvidenceSearchState = {
  assetId: string; allDocs: boolean; question: string;
  queryType: "auto" | "attribute" | "document"; attributeKey?: string; page: number;
};
const keys = ["q", "scope", "asset", "search", "field", "page"];

export function parseEvidenceSearch(params: Record<string, string | string[] | undefined>, assetIds: string[]): EvidenceSearchState | null {
  if (keys.some(key => Array.isArray(params[key]))) return null;
  const value = (key: string) => typeof params[key] === "string" ? params[key] as string : "";
  const question = value("q").trim(), scope = value("scope"), assetId = value("asset");
  const queryType = value("search"), attributeKey = value("field");
  const pageText = value("page") || "1", page = Number(pageText);
  if (question.length < 2 || question.length > 1000 || !["asset", "corpus"].includes(scope)) return null;
  if (scope === "asset" ? !assetIds.includes(assetId) : !!assetId) return null;
  if (queryType !== "auto" && queryType !== "attribute" && queryType !== "document") return null;
  if (scope === "corpus" && (queryType !== "document" || attributeKey)) return null;
  if (attributeKey && (queryType !== "attribute" || !/^[a-zA-Z0-9_]{1,100}$/.test(attributeKey))) return null;
  if (!/^[1-9]\d{0,4}$/.test(pageText) || !Number.isSafeInteger(page) || page > 10000) return null;
  return { assetId, allDocs: scope === "corpus", question, queryType, ...(attributeKey ? { attributeKey } : {}), page };
}

export function evidenceSearchUrl(href: string, state: EvidenceSearchState | null): string {
  const url = new URL(href, "http://local.invalid");
  for (const key of keys) url.searchParams.delete(key);
  if (state) {
    url.searchParams.set("q", state.question);
    url.searchParams.set("scope", state.allDocs ? "corpus" : "asset");
    if (!state.allDocs) url.searchParams.set("asset", state.assetId);
    url.searchParams.set("search", state.queryType);
    if (state.attributeKey) url.searchParams.set("field", state.attributeKey);
    url.searchParams.set("page", String(state.page));
  }
  return `${url.pathname}${url.search}${url.hash}`;
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

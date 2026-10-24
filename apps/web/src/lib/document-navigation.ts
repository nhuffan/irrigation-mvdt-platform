const APP_ORIGIN = "https://app.invalid";
const UUID = "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}";
const VIEW = new RegExp(`^/(?:ai-research-preview|methodology|map|assets/${UUID}|reservoirs/${UUID}(?:/3d)?|data-sources/${UUID}/documents|documents/${UUID})?$`, "i");
const MAX_RETURN_LENGTH = 8192;
const MAX_RETURN_DEPTH = 6;

/** A return path identifies an application view, never an arbitrary URL or API. */
export function documentReturnTo(value: unknown, depth = 0): string | null {
  if (typeof value !== "string" || value.length > MAX_RETURN_LENGTH || depth > MAX_RETURN_DEPTH || !value.startsWith("/") || value.startsWith("//") || /[\\\s\u0000-\u001f\u007f]/.test(value) || /%(?![a-f0-9]{2})/i.test(value)) return null;
  try {
    const url = new URL(value, APP_ORIGIN);
    // Reject normalized traversal and encoded route separators rather than
    // accepting a different view after URL normalization.
    if (url.origin !== APP_ORIGIN || value.split(/[?#]/)[0] !== url.pathname || !VIEW.test(url.pathname)) return null;
    if (/[\\\u0000-\u001f\u007f]/.test(decodeURIComponent(value))) return null;
    const parents = url.searchParams.getAll("returnTo");
    if (parents.length > 1 || (parents.length === 1 && !documentReturnTo(parents[0], depth + 1))) return null;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch { return null; }
}

/** Retain the target's own filters/physical page/anchor while adding its origin. */
export function documentHref(href: string, origin: string): string {
  const target = documentReturnTo(href), returnTo = documentReturnTo(origin);
  if (!target || !returnTo) return href;
  const url = new URL(target, APP_ORIGIN), source = new URL(returnTo, APP_ORIGIN);
  if (url.pathname === source.pathname) {
    const parent = source.searchParams.get("returnTo");
    if (parent && !url.searchParams.has("returnTo")) url.searchParams.set("returnTo", parent);
    return `${url.pathname}${url.search}${url.hash}`;
  }
  url.searchParams.set("returnTo", returnTo);
  let result = `${url.pathname}${url.search}${url.hash}`;
  if (!documentReturnTo(result)) {
    // Keep the immediate origin if an unusually long drilldown would otherwise
    // grow without bound. No result bodies or source text are persisted.
    source.searchParams.delete("returnTo");
    url.searchParams.set("returnTo", `${source.pathname}${source.search}${source.hash}`);
    result = `${url.pathname}${url.search}${url.hash}`;
  }
  return documentReturnTo(result) ? result : href;
}

export function documentBackLabel(href: string): string {
  const path = href.split(/[?#]/)[0];
  if (path === "/ai-research-preview") return "Back to AI Research";
  if (path === "/methodology") return "Back to Methodology";
  if (path === "/map") return "Back to map";
  if (path.startsWith("/assets/")) return "Back to asset";
  if (path.startsWith("/data-sources/")) return "Back to source documents";
  if (path.startsWith("/documents/")) return "Back to document";
  if (path.endsWith("/3d")) return "Back to 3D view";
  if (path.startsWith("/reservoirs/") && /[?&]asset=|#asset-gis|#assets/.test(href)) return "Back to asset explorer";
  return "Back to overview";
}

/** Physical PDF pages are one-based and bounded by the retained original. */
export function documentPage(value: unknown, pageCount: number | null): number {
  if (typeof value !== "string" || !/^[1-9]\d{0,4}$/.test(value)) return 1;
  const page = Number(value);
  return page <= (pageCount ?? 10000) ? page : 1;
}

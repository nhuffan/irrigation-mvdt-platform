/** Only application views can be used as document return destinations. */
export function documentReturnTo(value: unknown): string | null {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//") || /[\\\s\u0000-\u001f]/.test(value)) return null;
  const url = new URL(value, "https://app.invalid");
  if (url.origin !== "https://app.invalid") return null;
  if (!/^\/(?:ai-research-preview|methodology|map|assets\/[a-f0-9-]+|reservoirs\/[a-f0-9-]+(?:\/3d)?|data-sources\/[a-f0-9-]+\/documents|documents\/[a-f0-9-]+)?$/i.test(url.pathname)) return null;
  return `${url.pathname}${url.search}${url.hash}`;
}

export function documentHref(href: string, origin: string): string {
  const returnTo = documentReturnTo(origin);
  return returnTo ? `${href}?returnTo=${encodeURIComponent(returnTo)}` : href;
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
  return "Back to overview";
}

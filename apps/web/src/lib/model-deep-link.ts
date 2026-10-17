export function modelSelectionUrl(href: string, modelId: string, object: string | null) {
  const url = new URL(href);
  url.searchParams.set("model", modelId);
  if (object) url.searchParams.set("object", object);
  else url.searchParams.delete("object");
  return url.pathname + url.search + url.hash;
}
export function uniqueObjectLink<T extends { object_key: string }>(links: T[], key: string | null): T | undefined {
  const matches = links.filter(link => key !== null && link.object_key === key);
  return matches.length === 1 ? matches[0] : undefined;
}

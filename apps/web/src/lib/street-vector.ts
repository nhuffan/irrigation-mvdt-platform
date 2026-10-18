import type { StyleSpecification } from "maplibre-gl";
import { SatelliteProviderError, type SatelliteConfig, type ObservationLayer } from "./satellite-provider.ts";

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new SatelliteProviderError("METADATA_INVALID");
  return value as Record<string, unknown>;
}
function providerResource(value: unknown, key: string) {
  if (typeof value !== "string") throw new SatelliteProviderError("METADATA_INVALID");
  let url: URL;
  try { url = new URL(value); } catch { throw new SatelliteProviderError("METADATA_INVALID"); }
  if (url.protocol !== "https:" || url.hostname !== "api.maptiler.com" || url.port || url.username || url.password || url.hash) throw new SatelliteProviderError("METADATA_INVALID");
  // Preserve font/sprite placeholders; URL.href would encode their braces.
  return url.searchParams.has("key") ? value : `${value}${url.search ? "&" : "?"}key=${encodeURIComponent(key)}`;
}
/** Complete provider StyleJSON retains vector lines/text, glyphs and sprites at display resolution. */
export async function loadStreetVectorLayer(config: SatelliteConfig, signal: AbortSignal, fetcher: typeof fetch = fetch): Promise<ObservationLayer> {
  if (config.status !== "CONFIGURED" || config.provider !== "maptiler") throw new SatelliteProviderError("AUTH_REQUIRED");
  try {
    signal.throwIfAborted();
    const response = await fetcher(`https://api.maptiler.com/maps/streets/style.json?key=${encodeURIComponent(config.key)}`, { signal, credentials: "omit" });
    signal.throwIfAborted();
    if ([401, 403].includes(response.status)) throw new SatelliteProviderError("AUTH_REQUIRED");
    if (response.status === 429) throw new SatelliteProviderError("QUOTA_EXCEEDED");
    if (!response.ok) throw new SatelliteProviderError("PROVIDER_UNAVAILABLE");
    const style = object(await response.json()); signal.throwIfAborted();
    const sources = object(style.sources);
    if (style.version !== 8 || !Array.isArray(style.layers) || !style.layers.length || !Object.keys(sources).length) throw new SatelliteProviderError("METADATA_INVALID");
    const used = new Set<string>();
    for (const raw of style.layers) {
      const layer = object(raw);
      if (typeof layer.source === "string") {
        if (!sources[layer.source]) throw new SatelliteProviderError("METADATA_INVALID");
        used.add(layer.source);
      }
    }
    if (!used.size) throw new SatelliteProviderError("METADATA_INVALID");
    for (const [name, raw] of Object.entries(sources)) {
      const source = object(raw);
      if (source.type !== "vector" || source.tiles !== undefined) throw new SatelliteProviderError("METADATA_INVALID");
      // MapTiler includes an unused source solely to carry mandatory attribution.
      if (source.url === undefined && !used.has(name) && typeof source.attribution === "string" && source.tiles === undefined) continue;
      source.url = providerResource(source.url, config.key);
    }
    style.glyphs = providerResource(style.glyphs, config.key);
    if (typeof style.sprite === "string") style.sprite = providerResource(style.sprite, config.key);
    else if (Array.isArray(style.sprite) && style.sprite.length) for (const value of style.sprite) { const sprite = object(value); sprite.url = providerResource(sprite.url, config.key); }
    else throw new SatelliteProviderError("METADATA_INVALID");
    return { id: "street", kind: "street", provider: "maptiler", renderMode: "vector", style: style as unknown as StyleSpecification,
      name: "MapTiler Streets · vector map", date: "Cartographic map; not satellite imagery",
      resolution: "Vector labels and lines stay sharp as you zoom; feature coverage depends on source data",
      tiles: [], tileSize: 512, minzoom: 0, maxzoom: 18, detailMaxZoom: 18,
      attribution: '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> | &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
      sourceUrl: "https://docs.maptiler.com/cloud/api/maps/" };
  } catch (error) {
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    if (error instanceof SatelliteProviderError) throw error;
    throw new SatelliteProviderError("PROVIDER_UNAVAILABLE");
  }
}

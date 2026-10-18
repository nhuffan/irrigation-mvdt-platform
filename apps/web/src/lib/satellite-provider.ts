import type { StyleSpecification } from "maplibre-gl";
import { OBSERVATION_LAYERS } from "./observation-map.ts";
export type Provider = "maptiler" | "esri";
export type SatelliteConfig =
  | { status: "CONFIGURED"; provider: Provider; key: string }
  | { status: "CONFIGURATION_REQUIRED"; provider: Provider; reason: "MISSING_KEY" | "INVALID_KEY" | "INVALID_PROVIDER" };
export type ObservationLayer = {
  id: string; kind: "satellite" | "historical" | "street"; provider: Provider | "nasa" | "osm";
  name: string; date: string; resolution: string; tiles: string[]; tileSize: number;
  minzoom: number; maxzoom: number; detailMaxZoom?: number; renderMode?: "vector"; style?: StyleSpecification; attribution: string; sourceUrl: string;
};
export type ProviderErrorCode = "AUTH_REQUIRED" | "QUOTA_EXCEEDED" | "COVERAGE_UNAVAILABLE" | "PROVIDER_UNAVAILABLE" | "METADATA_INVALID";
export class SatelliteProviderError extends Error {
  code: ProviderErrorCode;
  constructor(code: ProviderErrorCode) { super(code); this.code = code; this.name = "SatelliteProviderError"; }
}
export function satelliteConfig(input: { provider?: unknown; maptilerKey?: unknown; esriKey?: unknown }): SatelliteConfig {
  let provider = input.provider ?? "maptiler";
  if (provider === "auto") provider = input.esriKey ? "esri" : "maptiler";
  if (provider !== "esri" && provider !== "maptiler") return { status: "CONFIGURATION_REQUIRED", provider: "maptiler", reason: "INVALID_PROVIDER" };
  const key = provider === "esri" ? input.esriKey : input.maptilerKey;
  if (key === undefined || key === null || key === "") return { status: "CONFIGURATION_REQUIRED", provider, reason: "MISSING_KEY" };
  if (typeof key !== "string" || !/^[A-Za-z0-9._~-]{8,8192}$/.test(key) || /^(your|replace|example|<)/i.test(key)) {
    return { status: "CONFIGURATION_REQUIRED", provider, reason: "INVALID_KEY" };
  }
  return { status: "CONFIGURED", provider, key };
}
export const STREET_LAYER: ObservationLayer = {
  id: "street", kind: "street", provider: "osm", name: "OpenStreetMap · street map", date: "Community map; not satellite imagery",
  resolution: "Cartographic detail; not an asset survey", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
  tileSize: 256, minzoom: 0, maxzoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
  sourceUrl: "https://operations.osmfoundation.org/policies/tiles/",
};
export const HISTORICAL_LAYERS: ObservationLayer[] = OBSERVATION_LAYERS.map(l => ({ ...l,
  kind: "historical", provider: "nasa", tiles: [l.tiles], tileSize: 256, minzoom: 0,
  attribution: 'Imagery: <a href="https://nasa-gibs.github.io/gibs-api-docs/">NASA GIBS / ESDIS</a> · Landsat / USGS, Terra / MODIS',
  sourceUrl: "https://nasa-gibs.github.io/gibs-api-docs/",
}));
// MapLibre's camera uses a 512px world tile; 256px rasters request camera z+1.
export function cameraZoomLimit(layer: Pick<ObservationLayer, "maxzoom" | "tileSize" | "detailMaxZoom" | "renderMode">) {
  if (layer.renderMode === "vector") return Math.min(layer.detailMaxZoom ?? 18, 18);
  return Math.max(0, Math.min(layer.detailMaxZoom ?? 18, 18, layer.maxzoom - Math.log2(512 / layer.tileSize)));
}
export function effectiveTileZoom(cameraZoom: number, layer: Pick<ObservationLayer, "minzoom" | "maxzoom" | "tileSize">) {
  return Math.max(layer.minzoom, Math.min(layer.maxzoom, Math.round(cameraZoom + Math.log2(512 / layer.tileSize))));
}
export function cappedCameraZoom(zoom: number, layer: Pick<ObservationLayer, "maxzoom" | "tileSize" | "detailMaxZoom" | "renderMode">) {
  return Math.max(0, Math.min(zoom, cameraZoomLimit(layer)));
}
export function providerFailureMessage(code: ProviderErrorCode) {
  return {
    AUTH_REQUIRED: "Satellite access was rejected. Check the owner key and allowed browser origins.",
    QUOTA_EXCEEDED: "Satellite quota or rate limit reached. Check the provider account before retrying.",
    COVERAGE_UNAVAILABLE: "Satellite imagery is unavailable at this location or zoom.",
    PROVIDER_UNAVAILABLE: "The satellite service could not be reached.",
    METADATA_INVALID: "Satellite metadata or tile dimensions could not be validated.",
  }[code];
}
export function redactProviderUrl(value: string) {
  return value.replace(/([?&](?:key|token|access_token|api_key)=)[^&#\s]*/gi, "$1[redacted]");
}
export function tileCoordinate(lon: number, lat: number, zoom: number) {
  const n = 2 ** zoom, latitude = Math.max(-85.05112878, Math.min(85.05112878, lat));
  return { x: Math.min(n - 1, Math.max(0, Math.floor((lon + 180) / 360 * n))),
    y: Math.min(n - 1, Math.max(0, Math.floor((1 - Math.asinh(Math.tan(latitude * Math.PI / 180)) / Math.PI) / 2 * n))) };
}
export function tileUrl(template: string, zoom: number, center: [number, number]) {
  const { x, y } = tileCoordinate(...center, zoom);
  return template.replaceAll("{z}", String(zoom)).replaceAll("{x}", String(x)).replaceAll("{y}", String(y));
}
function requireOK(response: Response) {
  if ([401, 403].includes(response.status)) throw new SatelliteProviderError("AUTH_REQUIRED");
  if (response.status === 429) throw new SatelliteProviderError("QUOTA_EXCEEDED");
  if ([204, 404].includes(response.status)) throw new SatelliteProviderError("COVERAGE_UNAVAILABLE");
  if (!response.ok) throw new SatelliteProviderError("PROVIDER_UNAVAILABLE");
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new SatelliteProviderError("METADATA_INVALID");
  return value as Record<string, unknown>;
}
function tileTemplate(value: unknown, provider: Provider) {
  if (typeof value !== "string") throw new SatelliteProviderError("METADATA_INVALID");
  const url = new URL(value);
  const host = provider === "maptiler" ? "api.maptiler.com" : "ibasemaps-api.arcgis.com";
  if (url.protocol !== "https:" || url.hostname !== host || url.port || url.username || url.password || !["{z}", "{x}", "{y}"].every(s => value.includes(s))) {
    throw new SatelliteProviderError("METADATA_INVALID");
  }
  return value;
}
function zoomRange(min: unknown, max: unknown) {
  if (!Number.isInteger(min) || !Number.isInteger(max) || (min as number) < 0 || (max as number) < (min as number) || (max as number) > 24) {
    throw new SatelliteProviderError("METADATA_INVALID");
  }
  return { minzoom: min as number, maxzoom: max as number };
}
/** Keep provider text/link credits; remove active HTML and credential-bearing URLs. */
export function attributionHTML(value: string) {
  const doc = new DOMParser().parseFromString(value, "text/html");
  const parent = document.createElement("span");
  for (const node of Array.from(doc.body.childNodes)) append(node, parent);
  function append(node: Node, target: HTMLElement) {
    if (node.nodeType === Node.TEXT_NODE) { target.append(document.createTextNode(node.textContent ?? "")); return; }
    if (!(node instanceof Element) || ["SCRIPT", "STYLE", "IFRAME"].includes(node.tagName)) return;
    if (node.tagName === "A") {
      try {
        const url = new URL(node.getAttribute("href") ?? "");
        if (["https:", "http:"].includes(url.protocol) && !/[?&](key|token|access_token|api_key)=/i.test(url.search)) {
          const link = document.createElement("a"); link.href = url.href; link.target = "_blank"; link.rel = "noreferrer";
          for (const child of Array.from(node.childNodes)) append(child, link);
          target.append(link); return;
        }
      } catch { /* Retain text for unsafe or relative links. */ }
    }
    for (const child of Array.from(node.childNodes)) append(child, target);
  }
  return parent.innerHTML;
}
export type TileDecoder = (response: Response) => Promise<{ width: number; height: number }>;
async function decodeTile(response: Response) {
  const bitmap = await createImageBitmap(await response.blob());
  const size = { width: bitmap.width, height: bitmap.height }; bitmap.close(); return size;
}
/** All network requests are direct browser requests using an owner-authorized public key. */
export async function loadSatelliteLayer(config: SatelliteConfig, center: [number, number], signal: AbortSignal,
  fetcher: typeof fetch = fetch, decoder: TileDecoder = decodeTile): Promise<ObservationLayer> {
  if (config.status !== "CONFIGURED") throw new SatelliteProviderError("AUTH_REQUIRED");
  try {
    signal.throwIfAborted();
    let meta: Record<string, unknown>, templates: string[], range: { minzoom: number; maxzoom: number }, credits: string;
    if (config.provider === "maptiler") {
      // Discover the actual raster tileset from MapTiler's maintained Satellite style.
      // Versioned examples (e.g. satellite-v4) need not exist for this service/account.
      const styleResponse = await fetcher(`https://api.maptiler.com/maps/satellite/style.json?key=${encodeURIComponent(config.key)}`, { signal, credentials: "omit" });
      signal.throwIfAborted(); requireOK(styleResponse);
      const style = record(await styleResponse.json()); signal.throwIfAborted();
      const sources = record(style.sources);
      if (!Array.isArray(style.layers)) throw new SatelliteProviderError("METADATA_INVALID");
      const used = new Set(style.layers.flatMap(value => {
        const layer = record(value);
        return layer.type === "raster" && typeof layer.source === "string" ? [layer.source] : [];
      }));
      if (used.size !== 1) throw new SatelliteProviderError("METADATA_INVALID");
      const raster = record(sources[[...used][0]]);
      if (raster.type !== "raster" || typeof raster.url !== "string") throw new SatelliteProviderError("METADATA_INVALID");
      const metadataUrl = new URL(raster.url);
      if (metadataUrl.protocol !== "https:" || metadataUrl.hostname !== "api.maptiler.com" || metadataUrl.port || metadataUrl.username || metadataUrl.password ||
        !/^\/tiles\/[A-Za-z0-9_.-]+\/tiles\.json$/.test(metadataUrl.pathname)) throw new SatelliteProviderError("METADATA_INVALID");
      const response = await fetcher(raster.url, { signal, credentials: "omit" });
      signal.throwIfAborted(); requireOK(response); meta = record(await response.json()); signal.throwIfAborted();
      if (!Array.isArray(meta.tiles) || !meta.tiles.length || typeof meta.attribution !== "string" || !meta.attribution.trim() ||
        (meta.scheme !== undefined && meta.scheme !== "xyz") ||
        (meta.crs !== undefined && !["EPSG:3857", "EPSG:900913"].includes(String(meta.crs))) ||
        (meta.format !== undefined && !["jpg", "jpeg", "png", "webp"].includes(String(meta.format).toLowerCase()))) throw new SatelliteProviderError("METADATA_INVALID");
      if (meta.tileSize === undefined && typeof raster.tileSize === "number") meta.tileSize = raster.tileSize;
      templates = meta.tiles.map(t => tileTemplate(t, "maptiler"));
      range = zoomRange(meta.minzoom ?? 0, meta.maxzoom); credits = meta.attribution;
      if (typeof raster.attribution === "string" && raster.attribution !== credits) credits += ` | ${raster.attribution}`;
      if (Array.isArray(meta.bounds) && meta.bounds.length === 4) {
        const [west, south, east, north] = meta.bounds.map(Number);
        if (![west, south, east, north].every(Number.isFinite) || center[0] < west || center[0] > east || center[1] < south || center[1] > north) throw new SatelliteProviderError("COVERAGE_UNAVAILABLE");
      }
    } else {
      const base = "https://ibasemaps-api.arcgis.com/arcgis/rest/services/World_Imagery/MapServer";
      const response = await fetcher(`${base}?f=json&token=${encodeURIComponent(config.key)}`, { signal, credentials: "omit" });
      signal.throwIfAborted(); requireOK(response); meta = record(await response.json()); signal.throwIfAborted();
      if (meta.error) {
        const error = record(meta.error);
        throw new SatelliteProviderError([401, 403, 498, 499].includes(Number(error.code)) ? "AUTH_REQUIRED" : Number(error.code) === 429 ? "QUOTA_EXCEEDED" : "PROVIDER_UNAVAILABLE");
      }
      const tileInfo = record(meta.tileInfo);
      const spatial = record(tileInfo.spatialReference);
      if (![3857, 102100, 102113].includes(Number(spatial.wkid)) || !Array.isArray(tileInfo.lods) || !tileInfo.lods.length || typeof meta.copyrightText !== "string" || !meta.copyrightText.trim()) throw new SatelliteProviderError("METADATA_INVALID");
      const levels = tileInfo.lods.map(l => Number(record(l).level));
      range = zoomRange(Math.min(...levels), Math.max(...levels));
      templates = [tileTemplate(`${base}/tile/{z}/{y}/{x}?token=${encodeURIComponent(config.key)}`, "esri")];
      // Service copyright is retained; the Esri provider link remains visible as well.
      credits = meta.copyrightText;
    }
    signal.throwIfAborted();
    const response = await fetcher(tileUrl(templates[0], Math.max(range.minzoom, Math.min(12, range.maxzoom)), center), { signal, credentials: "omit" });
    signal.throwIfAborted(); requireOK(response);
    if (!response.headers.get("content-type")?.startsWith("image/")) throw new SatelliteProviderError("METADATA_INVALID");
    const size = await decoder(response);
    signal.throwIfAborted();
    if (size.width !== size.height || ![256, 512].includes(size.width)) throw new SatelliteProviderError("METADATA_INVALID");
    if (typeof meta.tileSize === "number" && meta.tileSize !== size.width) throw new SatelliteProviderError("METADATA_INVALID");
    return { id: "satellite", kind: "satellite", provider: config.provider,
      name: config.provider === "maptiler" ? "MapTiler Satellite" : "Esri ArcGIS Imagery",
      date: "Provider mosaic; acquisition date varies and is not certified here",
      resolution: `Service tile levels ${range.minzoom}–${range.maxzoom}; local detail cap 16, higher levels may be resampled`,
      ...range, detailMaxZoom: 16, tileSize: size.width, tiles: templates, attribution: credits,
      sourceUrl: config.provider === "maptiler" ? "https://docs.maptiler.com/cloud/api/tiles/" : "https://developers.arcgis.com/rest/basemap-styles/service-data/" };
  } catch (error) {
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    if (error instanceof SatelliteProviderError) throw error;
    // Neither fetch errors nor parser messages (which can contain keyed URLs) escape.
    throw new SatelliteProviderError("PROVIDER_UNAVAILABLE");
  }
}

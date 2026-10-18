import { cameraZoomLimit, type ObservationLayer } from "./satellite-provider.ts";
export type PixelRendering = "smooth" | "original";
export function rasterClarityPaint(layer: Pick<ObservationLayer, "kind">, rendering: PixelRendering) {
  return { "raster-fade-duration": 0,
    "raster-resampling": layer.kind === "historical" && rendering === "original" ? "nearest" as const : "linear" as const };
}
/** Land on a source pixel grid instead of interpolating a fractional raster level. */
export function nativeDetailZoom(zoom: number, layer: ObservationLayer) {
  return Math.min(cameraZoomLimit(layer), Math.max(0, Math.round(zoom)));
}
export function closerDetailZoom(layer: ObservationLayer) {
  return layer.kind === "street" ? cameraZoomLimit(layer) : Math.min(16, cameraZoomLimit(layer));
}
export type StreetFailureAction = "USE_OSM" | "SHOW_ERROR";
export function streetFailureAction(usingVector: boolean, alreadyFallback: boolean): StreetFailureAction {
  return usingVector && !alreadyFallback ? "USE_OSM" : "SHOW_ERROR";
}

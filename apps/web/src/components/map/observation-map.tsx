"use client";
import { useEffect, useRef, useState } from "react";
import type { Map as LibreMap } from "maplibre-gl";
import type { Asset } from "@/types/asset";
import type { Reservoir } from "@/types/reservoir";
import { assetDisplayName } from "@/lib/asset-display";
import { observationReferences, OPERATOR_MAP_URL } from "@/lib/observation-map";
import { loadStreetVectorLayer } from "@/lib/street-vector";
import { rasterClarityPaint, nativeDetailZoom, closerDetailZoom, streetFailureAction, type PixelRendering } from "@/lib/observation-detail";
import { PanelSection } from "@/components/ui/panel-section";
import {
  satelliteConfig, STREET_LAYER, HISTORICAL_LAYERS, loadSatelliteLayer,
  cameraZoomLimit, cappedCameraZoom, effectiveTileZoom, attributionHTML,
  SatelliteProviderError, providerFailureMessage,
  type ObservationLayer, type ProviderErrorCode,
} from "@/lib/satellite-provider";

const config = satelliteConfig({ provider: process.env.NEXT_PUBLIC_SATELLITE_PROVIDER,
  maptilerKey: process.env.NEXT_PUBLIC_MAPTILER_KEY, esriKey: process.env.NEXT_PUBLIC_ARCGIS_API_KEY });
const staticLayers = [STREET_LAYER, ...HISTORICAL_LAYERS];

export function ObservationMap({ assets, reservoir }: { assets: Asset[]; reservoir: Reservoir }) {
  const section = useRef<HTMLElement>(null);
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<LibreMap | null>(null);
  const lastView = useRef<{ center: [number, number]; zoom: number } | null>(null);
  const nextZoom = useRef<number | null>(null);
  const [mounted, setMounted] = useState(false);
  const [layerId, setLayerId] = useState(config.status === "CONFIGURED" ? "satellite" : "street");
  const [activeLayer, setActiveLayer] = useState<ObservationLayer | null>(null);
  const [zoom, setZoom] = useState(9.5);
  const [streetFallback, setStreetFallback] = useState(false);
  const [rendering, setRendering] = useState<PixelRendering>("original");
  const [attempt, setAttempt] = useState(0);
  const [failure, setFailure] = useState<string | null>(null);
  const [status, setStatus] = useState<"waiting" | "loading" | "ready" | "error">("waiting");
  const vectorStreet = config.status === "CONFIGURED" && config.provider === "maptiler" && !streetFallback;
  const displayLayer = activeLayer ?? (layerId === "street" && vectorStreet ? null : staticLayers.find(l => l.id === layerId)) ?? null;

  useEffect(() => {
    if (!section.current) return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(e => e.isIntersecting)) { setMounted(true); observer.disconnect(); }
    });
    observer.observe(section.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!mounted || !container.current) return;
    const controller = new AbortController();
    let disposed = false, failed = false;
    let instance: LibreMap | undefined;
    let resize: ResizeObserver | undefined;
    const fail = (code: ProviderErrorCode = "PROVIDER_UNAVAILABLE") => {
      if (disposed || failed) return;
      failed = true;
      controller.abort();
      clearTimeout(timer);
      if (layerId !== "street") {
        setFailure(`${layerId === "satellite" ? providerFailureMessage(code) : "Historical imagery could not be loaded."} OpenStreetMap fallback selected.`);
        setStreetFallback(true); setLayerId("street");
      } else if (streetFailureAction(vectorStreet, streetFallback) === "USE_OSM") {
        setFailure("Vector street map could not be loaded. OpenStreetMap fallback selected.");
        setStreetFallback(true);
      } else setStatus("error"); // OSM failure never retries recursively.
    };
    const timer = setTimeout(() => fail(), 20000);
    async function start() {
      setStatus("loading"); setActiveLayer(null);
      try {
        const layer = layerId === "satellite"
          ? await loadSatelliteLayer(config, [reservoir.longitude, reservoir.latitude], controller.signal)
          : layerId === "street" && vectorStreet
            ? await loadStreetVectorLayer(config, controller.signal)
            : staticLayers.find(l => l.id === layerId) ?? STREET_LAYER;
        const lib = await import("maplibre-gl");
        if (disposed || controller.signal.aborted || !container.current) return;
        lib.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
        const rememberedZoom = lastView.current?.zoom ?? 10;
        const initialZoom = layer.renderMode === "vector" ? cappedCameraZoom(rememberedZoom, layer) : nativeDetailZoom(rememberedZoom, layer);
        instance = new lib.Map({ container: container.current,
          style: layer.style ?? { version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": "#e7eeeb" } }] },
          center: lastView.current?.center ?? [reservoir.longitude, reservoir.latitude], zoom: initialZoom,
          minZoom: Math.min(7, cameraZoomLimit(layer)), maxZoom: cameraZoomLimit(layer),
          cooperativeGestures: true, attributionControl: false,
        });
        map.current = instance;
        setActiveLayer(layer); setZoom(initialZoom);
        instance.addControl(new lib.NavigationControl(), "top-right");
        instance.addControl(new lib.FullscreenControl(), "top-right");
        instance.addControl(new lib.ScaleControl({ unit: "metric" }), "bottom-left");
        const extraCredits = layer.provider === "maptiler"
          ? ' | &copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> | &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
          : layer.provider === "esri" ? ' | <a href="https://www.esri.com/">Powered by Esri</a>' : "";
        instance.addControl(new lib.AttributionControl({ compact: false, customAttribution: attributionHTML(layer.attribution + extraCredits) }), "bottom-right");
        if (layer.provider === "maptiler") {
          const logo = document.createElement("a"); logo.className = "maplibregl-ctrl observation-provider-logo";
          logo.href = "https://www.maptiler.com/"; logo.target = "_blank"; logo.rel = "noreferrer";
          const img = document.createElement("img"); img.src = "https://api.maptiler.com/resources/logo.svg"; img.alt = "MapTiler logo"; img.width = 88;
          logo.append(img);
          instance.addControl({ onAdd: () => logo, onRemove: () => logo.remove() }, "bottom-left");
        }
        instance.on("error", () => fail()); // Never surface event.error: it can contain a keyed URL.
        instance.on("zoomend", () => {
          if (disposed || failed || !instance) return;
          const actual = instance.getZoom();
          const snapped = nativeDetailZoom(actual, layer);
          if (layer.renderMode !== "vector" && Math.abs(actual - snapped) > 0.01) { instance.jumpTo({ zoom: snapped }); return; }
          setZoom(actual);
        });
        instance.on("load", () => {
          if (disposed || failed || !instance) return;
          if (layer.renderMode === "vector") { clearTimeout(timer); setStatus("ready"); }
          else {
            instance.on("sourcedata", event => {
              if (!disposed && !failed && event.sourceId === "observation-imagery" && event.isSourceLoaded) {
                clearTimeout(timer); setStatus("ready");
              }
            });
            instance.addSource("observation-imagery", { type: "raster", tiles: layer.tiles,
              tileSize: layer.tileSize, minzoom: layer.minzoom, maxzoom: layer.maxzoom,
              attribution: attributionHTML(layer.attribution + extraCredits) });
            instance.addLayer({ id: "observation-imagery", type: "raster", source: "observation-imagery",
              paint: rasterClarityPaint(layer, "original") });
          }
          for (const asset of observationReferences(assets)) {
            const point = asset.location!.geometry!;
            if (point.type !== "Point") continue;
            const label = document.createElement("button"); label.className = "observation-reference"; label.textContent = "R";
            label.setAttribute("aria-label", `REFERENCE · ${assetDisplayName(asset)}`);
            label.title = "Reference only. Open details for the research GIS link.";
            const popupContent = document.createElement("div");
            const heading = document.createElement("strong"); heading.textContent = `REFERENCE · ${assetDisplayName(asset)}`;
            const note = document.createElement("p"); note.textContent = "Navigation reference only. Not surveyed geometry.";
            const link = document.createElement("a"); link.href = `/reservoirs/${asset.reservoir_id}?asset=${encodeURIComponent(asset.id)}#asset-gis`; link.textContent = "Open in research GIS →";
            popupContent.append(heading, note, link);
            new lib.Marker({ element: label }).setLngLat(point.coordinates)
              .setPopup(new lib.Popup({ maxWidth: "280px" }).setDOMContent(popupContent)).addTo(instance);
          }
        });
        resize = new ResizeObserver(() => instance?.resize()); resize.observe(container.current);
      } catch (error) {
        if (!disposed && !failed) fail(error instanceof SatelliteProviderError ? error.code : "PROVIDER_UNAVAILABLE");
      }
    }
    void start();
    return () => {
      disposed = true; controller.abort(); clearTimeout(timer); resize?.disconnect();
      if (instance) { const center = instance.getCenter(); lastView.current = { center: [center.lng, center.lat], zoom: nextZoom.current ?? instance.getZoom() }; nextZoom.current = null; instance.remove(); }
      map.current = null;
    };
  }, [mounted, layerId, streetFallback, vectorStreet, attempt, assets, reservoir.longitude, reservoir.latitude]);

  useEffect(() => {
    const instance = map.current;
    if (!activeLayer || status !== "ready" || activeLayer.renderMode === "vector" || !instance?.getLayer("observation-imagery")) return;
    const paint = rasterClarityPaint(activeLayer, rendering);
    instance.setPaintProperty("observation-imagery", "raster-resampling", paint["raster-resampling"]);
  }, [activeLayer, status, rendering]);

  function viewReferences() {
    const points = observationReferences(assets).flatMap(a => a.location?.geometry?.type === "Point" ? [a.location.geometry.coordinates] : []);
    if (!points.length || !activeLayer) return;
    map.current?.fitBounds([[Math.min(...points.map(p => p[0])), Math.min(...points.map(p => p[1]))], [Math.max(...points.map(p => p[0])), Math.max(...points.map(p => p[1]))]], { padding: 70, maxZoom: Math.min(13, cameraZoomLimit(activeLayer)) });
  }
  function retrySatellite() { setFailure(null); setLayerId("satellite"); setAttempt(a => a + 1); }
  function bestDetail() { if (activeLayer) map.current?.easeTo({ zoom: closerDetailZoom(activeLayer) }); }
  function detailedSatellite() {
    const instance = map.current;
    if (instance) nextZoom.current = Math.max(13, instance.getZoom());
    setFailure(null); setLayerId("satellite");
  }

  return <section id="secondary-observation-map" className="observation-section" ref={section} aria-labelledby="observation-heading">
    <PanelSection title="Satellite & Irrigation Context" description="Independent observation map · asset GIS is available in Overview">
      <h2 id="observation-heading" className="sr-only">Satellite &amp; Irrigation Context</h2>
      <p className="muted">Regional context around Dầu Tiếng. Basemap landmarks and reference markers do not verify asset locations, current condition or F02.</p>
      {config.status === "CONFIGURATION_REQUIRED" && <p className="observation-provider-status" role="status"><strong>High-resolution satellite · CONFIGURATION_REQUIRED</strong> · Showing a street-map fallback. An owner-authorized MapTiler or Esri browser key is required to enable satellite imagery.</p>}
      {failure && <div className="observation-provider-status" role="alert"><p>{failure}</p>{config.status === "CONFIGURED" && <><button className="text-link" onClick={retrySatellite}>Retry satellite provider</button>{layerId === "street" && streetFallback && config.provider === "maptiler" && <button className="text-link" onClick={() => { setFailure(null); setStreetFallback(false); }}>Retry vector street map</button>}</>}</div>}
      <div className="observation-toolbar"><label>Map layer <select value={layerId} onChange={e => { setFailure(null); setStreetFallback(false); setLayerId(e.target.value); }}>
        {config.status === "CONFIGURED" && <option value="satellite">Satellite · {config.provider === "maptiler" ? "MapTiler" : "Esri"}</option>}
        <option value="street">{config.status === "CONFIGURED" && config.provider === "maptiler" ? "Street map · MapTiler vector / OSM fallback" : "Street map · OpenStreetMap (not satellite)"}</option>
        {HISTORICAL_LAYERS.map(l => <option key={l.id} value={l.id}>Historical · {l.name} · {l.date}</option>)}
      </select></label>
        <button className="button button-secondary" disabled={status !== "ready" || !activeLayer} onClick={() => activeLayer && map.current?.flyTo({ center: [reservoir.longitude, reservoir.latitude], zoom: nativeDetailZoom(10, activeLayer) })}>Reset context view</button>
        <button className="button button-secondary" disabled={status !== "ready" || !observationReferences(assets).length} onClick={viewReferences}>View reviewed references</button>
        <button className="button button-secondary" disabled={status !== "ready" || !activeLayer} onClick={bestDetail}>Best available detail</button>
        {displayLayer?.kind === "historical" && <label>Historical pixels <select value={rendering} onChange={e => setRendering(e.target.value as PixelRendering)}><option value="original">Original pixels · no smoothing</option><option value="smooth">Smooth rendering</option></select></label>}
      </div>
      <p className="observation-layer-note">{displayLayer ? <>{displayLayer.name} · {displayLayer.date} · {displayLayer.resolution}.</> : "Reading authorized provider metadata…"}</p>
      {activeLayer && <div className="observation-resolution" role="status">{zoom >= cameraZoomLimit(activeLayer) - 0.25 ? `${activeLayer.kind === "street" ? "Map detail" : "Imagery resolution"} limit · ` : ""}Zoom {zoom.toFixed(1)} / {cameraZoomLimit(activeLayer)} · {activeLayer.renderMode === "vector" ? "Vector labels and lines rendered at screen resolution." : `Source tile ${effectiveTileZoom(zoom, activeLayer)} / ${activeLayer.maxzoom} · ${activeLayer.tileSize}px. Native zoom steps avoid fractional pixel smoothing.`}
        {activeLayer.kind === "historical" && <p>Historical {activeLayer.id === "landsat" ? "30 m" : "250 m"} imagery cannot reveal smaller features. Original pixels change rendering only.</p>}
        {activeLayer.kind === "historical" && config.status === "CONFIGURED" && <button className="text-link" onClick={detailedSatellite}>Switch to detailed satellite →</button>}
      </div>}
      <div className="observation-map-frame"><div ref={container} className="observation-canvas" role="region" aria-label="Independent observation map with labeled basemap provider" tabIndex={0}/>
        {status !== "ready" && <div className="observation-overlay" role={status === "error" ? "alert" : "status"}>
          {status === "waiting" ? "Observation map loads when this section enters the viewport." : status === "loading" ? "Loading observation map…" : <><strong>Observation map unavailable</strong><p>Coverage, WebGL or the remote service could not be loaded. No substitute geography is inferred.</p><button className="button button-secondary" onClick={() => setAttempt(a => a + 1)}>Retry map</button><a href={OPERATOR_MAP_URL} target="_blank" rel="noreferrer">Open operator map source ↗</a></>}
        </div>}
      </div>
      <p className="observation-layer-note">Reviewed references: {observationReferences(assets).length ? observationReferences(assets).map(a => <a className="text-link" key={a.id} href={`/reservoirs/${a.reservoir_id}?asset=${encodeURIComponent(a.id)}#asset-gis`}>REFERENCE · {assetDisplayName(a)} </a>) : "None available"}</p>
      <p className="observation-attribution">{displayLayer?.provider === "osm" ? <><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a> · Street map, not satellite imagery.</> : displayLayer?.provider === "nasa" ? <>Historical imagery: <a href="https://nasa-gibs.github.io/gibs-api-docs/" target="_blank" rel="noreferrer">NASA GIBS / ESDIS</a> · Landsat / USGS, Terra / MODIS.</> : displayLayer?.provider === "maptiler" ? <><a href="https://www.maptiler.com/copyright/" target="_blank" rel="noreferrer">© MapTiler</a> · Dataset contributor credits are retained on the map.</> : displayLayer?.provider === "esri" ? <><a href="https://www.esri.com/" target="_blank" rel="noreferrer">Powered by Esri</a> · Service contributor credits are retained on the map.</> : null} {displayLayer && <a href={displayLayer.sourceUrl} target="_blank" rel="noreferrer">Provider documentation ↗</a>}</p>
      <details className="observation-notes"><summary>Scope, sources and navigation</summary><p>Drag to pan; use +/− or keyboard arrows to navigate. Hold Ctrl/⌘ while scrolling to zoom; use two fingers on mobile. Fullscreen applies to this map only. Open Overview for the asset GIS and evidence inspector.</p><p>NASA layers are low-resolution historical overviews, with zoom capped at their source limit. The street layer uses vector lines/text when MapTiler is available, with OpenStreetMap raster fallback. Raster zoom rests on native integer levels and tile transitions do not blend lower-detail parents. Original-pixel rendering makes historical pixels distinct, not higher resolution. Satellite service levels do not guarantee building detail or surveyed accuracy. Acquisition dates and local high-zoom detail require separate evidence.</p><p>Only reviewed REFERENCE points from the API are displayed. No INTAKE/MGMT coordinates, canonical geometry, local GLB-to-WGS84 transform, canal lines or inferred asset positions are added. The initial camera uses registry context metadata and is not a surveyed reservoir extent.</p><p>The operator map is linked for consultation; no right to copy or rehost it was established. <a href={OPERATOR_MAP_URL} target="_blank" rel="noreferrer">Operator map source ↗</a> · <a href="https://siwrp.org.vn/news/ban-do_520.html" target="_blank" rel="noreferrer">SIWRP map catalogue ↗</a>. Their publications are not layers in this map.</p></details>
    </PanelSection>
  </section>;
}

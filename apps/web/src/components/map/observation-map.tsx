"use client";
import { useEffect, useRef, useState } from "react";
import type { Map as LibreMap } from "maplibre-gl";
import type { Asset } from "@/types/asset";
import type { Reservoir } from "@/types/reservoir";
import { assetDisplayName } from "@/lib/asset-display";
import { observationReferences, OPERATOR_MAP_URL } from "@/lib/observation-map";
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
  const [mounted, setMounted] = useState(false);
  const [layerId, setLayerId] = useState(config.status === "CONFIGURED" ? "satellite" : "street");
  const [activeLayer, setActiveLayer] = useState<ObservationLayer | null>(null);
  const [zoom, setZoom] = useState(9.5);
  const [attempt, setAttempt] = useState(0);
  const [failure, setFailure] = useState<string | null>(null);
  const [status, setStatus] = useState<"waiting" | "loading" | "ready" | "error">("waiting");
  const displayLayer = activeLayer ?? staticLayers.find(l => l.id === layerId) ?? null;

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
        setFailure(layerId === "satellite" ? providerFailureMessage(code) : "Historical imagery could not be loaded.");
        setLayerId("street"); // One fallback; a street-map failure never retries recursively.
      } else setStatus("error");
    };
    const timer = setTimeout(() => fail(), 20000);
    async function start() {
      setStatus("loading"); setActiveLayer(null);
      try {
        const layer = layerId === "satellite"
          ? await loadSatelliteLayer(config, [reservoir.longitude, reservoir.latitude], controller.signal)
          : staticLayers.find(l => l.id === layerId) ?? STREET_LAYER;
        const lib = await import("maplibre-gl");
        if (disposed || controller.signal.aborted || !container.current) return;
        lib.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
        const initialZoom = cappedCameraZoom(lastView.current?.zoom ?? 9.5, layer);
        instance = new lib.Map({ container: container.current,
          style: { version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": "#e7eeeb" } }] },
          center: lastView.current?.center ?? [reservoir.longitude, reservoir.latitude], zoom: initialZoom,
          minZoom: Math.min(7, cameraZoomLimit(layer)), maxZoom: cameraZoomLimit(layer),
          cooperativeGestures: true, attributionControl: false,
        });
        map.current = instance;
        setActiveLayer(layer); setZoom(initialZoom);
        instance.addControl(new lib.NavigationControl(), "top-right");
        instance.addControl(new lib.FullscreenControl(), "top-right");
        instance.addControl(new lib.ScaleControl({ unit: "metric" }), "bottom-left");
        instance.addControl(new lib.AttributionControl({ compact: false }), "bottom-right");
        if (layer.provider === "maptiler") {
          const logo = document.createElement("a"); logo.className = "maplibregl-ctrl observation-provider-logo";
          logo.href = "https://www.maptiler.com/"; logo.target = "_blank"; logo.rel = "noreferrer";
          const img = document.createElement("img"); img.src = "https://api.maptiler.com/resources/logo.svg"; img.alt = "MapTiler logo"; img.width = 88;
          logo.append(img);
          instance.addControl({ onAdd: () => logo, onRemove: () => logo.remove() }, "bottom-left");
        }
        instance.on("error", () => fail()); // Never surface event.error: it can contain a keyed URL.
        instance.on("zoomend", () => { if (!disposed && instance) setZoom(instance.getZoom()); });
        instance.on("load", () => {
          if (disposed || !instance) return;
          const extraCredits = layer.provider === "maptiler"
            ? ' | &copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> | &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
            : layer.provider === "esri" ? ' | <a href="https://www.esri.com/">Powered by Esri</a>' : "";
          instance.on("sourcedata", event => {
            if (!disposed && !failed && event.sourceId === "observation-imagery" && event.isSourceLoaded) {
              clearTimeout(timer); setStatus("ready");
            }
          });
          instance.addSource("observation-imagery", { type: "raster", tiles: layer.tiles,
            tileSize: layer.tileSize, minzoom: layer.minzoom, maxzoom: layer.maxzoom,
            attribution: attributionHTML(layer.attribution + extraCredits) });
          instance.addLayer({ id: "observation-imagery", type: "raster", source: "observation-imagery" });
          for (const asset of observationReferences(assets)) {
            const point = asset.location!.geometry!;
            if (point.type !== "Point") continue;
            const label = document.createElement("button"); label.className = "observation-reference"; label.textContent = "R";
            label.setAttribute("aria-label", `REFERENCE · ${assetDisplayName(asset)}`);
            label.title = "Reference only. Open details for the research GIS link.";
            const popupContent = document.createElement("div");
            const heading = document.createElement("strong"); heading.textContent = `REFERENCE · ${assetDisplayName(asset)}`;
            const note = document.createElement("p"); note.textContent = "Navigation reference only. Not surveyed geometry.";
            const link = document.createElement("a"); link.href = `/map?asset=${encodeURIComponent(asset.id)}`; link.textContent = "Open in research GIS →";
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
      if (instance) { const center = instance.getCenter(); lastView.current = { center: [center.lng, center.lat], zoom: instance.getZoom() }; instance.remove(); }
      map.current = null;
    };
  }, [mounted, layerId, attempt, assets, reservoir.longitude, reservoir.latitude]);

  function viewReferences() {
    const points = observationReferences(assets).flatMap(a => a.location?.geometry?.type === "Point" ? [a.location.geometry.coordinates] : []);
    if (!points.length || !activeLayer) return;
    map.current?.fitBounds([[Math.min(...points.map(p => p[0])), Math.min(...points.map(p => p[1]))], [Math.max(...points.map(p => p[0])), Math.max(...points.map(p => p[1]))]], { padding: 70, maxZoom: Math.min(13, cameraZoomLimit(activeLayer)) });
  }
  function retrySatellite() { setFailure(null); setLayerId("satellite"); setAttempt(a => a + 1); }

  return <section id="secondary-observation-map" className="observation-section" ref={section} aria-labelledby="observation-heading">
    <PanelSection title="Satellite & Irrigation Context" description="Independent observation map · secondary to the research GIS above">
      <h2 id="observation-heading" className="sr-only">Satellite &amp; Irrigation Context</h2>
      <p className="muted">Regional context around Dầu Tiếng. Basemap landmarks and reference markers do not verify asset locations, current condition or F02.</p>
      {config.status === "CONFIGURATION_REQUIRED" && <p className="observation-provider-status" role="status"><strong>High-resolution satellite · CONFIGURATION_REQUIRED</strong> · Showing a street-map fallback. An owner-authorized MapTiler or Esri browser key is required to enable satellite imagery.</p>}
      {failure && <div className="observation-provider-status" role="alert"><p>{failure} Street-map fallback selected.</p>{config.status === "CONFIGURED" && <button className="text-link" onClick={retrySatellite}>Retry satellite provider</button>}</div>}
      <div className="observation-toolbar"><label>Map layer <select value={layerId} onChange={e => { setFailure(null); setLayerId(e.target.value); }}>
        {config.status === "CONFIGURED" && <option value="satellite">Satellite · {config.provider === "maptiler" ? "MapTiler" : "Esri"}</option>}
        <option value="street">Street map · OpenStreetMap (not satellite)</option>
        {HISTORICAL_LAYERS.map(l => <option key={l.id} value={l.id}>Historical · {l.name} · {l.date}</option>)}
      </select></label>
        <button className="button button-secondary" disabled={status !== "ready" || !activeLayer} onClick={() => activeLayer && map.current?.flyTo({ center: [reservoir.longitude, reservoir.latitude], zoom: cappedCameraZoom(9.5, activeLayer) })}>Reset context view</button>
        <button className="button button-secondary" disabled={status !== "ready" || !observationReferences(assets).length} onClick={viewReferences}>View reviewed references</button>
      </div>
      <p className="observation-layer-note">{displayLayer ? <>{displayLayer.name} · {displayLayer.date} · {displayLayer.resolution}.</> : "Reading authorized provider metadata…"}</p>
      {activeLayer && <p className="observation-resolution" role="status">{zoom >= cameraZoomLimit(activeLayer) - 0.25 ? `${activeLayer.kind === "street" ? "Map detail" : "Imagery resolution"} limit · ` : ""}Camera zoom {zoom.toFixed(1)} / {cameraZoomLimit(activeLayer)} · tile zoom {effectiveTileZoom(zoom, activeLayer)} / {activeLayer.maxzoom} · {activeLayer.tileSize}px tiles. Zoom is capped to source limits and the observed local detail limit; provider imagery detail can still vary.</p>}
      <div className="observation-map-frame"><div ref={container} className="observation-canvas" role="region" aria-label="Independent observation map with labeled basemap provider" tabIndex={0}/>
        {status !== "ready" && <div className="observation-overlay" role={status === "error" ? "alert" : "status"}>
          {status === "waiting" ? "Observation map loads when this section enters the viewport." : status === "loading" ? "Loading observation map…" : <><strong>Observation map unavailable</strong><p>Coverage, WebGL or the remote service could not be loaded. No substitute geography is inferred.</p><button className="button button-secondary" onClick={() => setAttempt(a => a + 1)}>Retry map</button><a href={OPERATOR_MAP_URL} target="_blank" rel="noreferrer">Open operator map source ↗</a></>}
        </div>}
      </div>
      <p className="observation-layer-note">Reviewed references: {observationReferences(assets).length ? observationReferences(assets).map(a => <a className="text-link" key={a.id} href={`/map?asset=${a.id}`}>REFERENCE · {assetDisplayName(a)} </a>) : "None available"}</p>
      <p className="observation-attribution">{displayLayer?.provider === "osm" ? <><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a> · Street map, not satellite imagery.</> : displayLayer?.provider === "nasa" ? <>Historical imagery: <a href="https://nasa-gibs.github.io/gibs-api-docs/" target="_blank" rel="noreferrer">NASA GIBS / ESDIS</a> · Landsat / USGS, Terra / MODIS.</> : displayLayer?.provider === "maptiler" ? <><a href="https://www.maptiler.com/copyright/" target="_blank" rel="noreferrer">© MapTiler</a> · Dataset contributor credits are retained on the map.</> : displayLayer?.provider === "esri" ? <><a href="https://www.esri.com/" target="_blank" rel="noreferrer">Powered by Esri</a> · Service contributor credits are retained on the map.</> : null} {displayLayer && <a href={displayLayer.sourceUrl} target="_blank" rel="noreferrer">Provider documentation ↗</a>}</p>
      <details className="observation-notes"><summary>Scope, sources and navigation</summary><p>Drag to pan; use +/− or keyboard arrows to navigate. Hold Ctrl/⌘ while scrolling to zoom; use two fingers on mobile. Fullscreen applies to this map only. Neither map changes the other map&apos;s camera.</p><p>NASA layers are low-resolution historical overviews, with zoom capped at their source limit. The street map is a cartographic fallback. Satellite service levels do not guarantee building detail or surveyed accuracy. Acquisition dates and local high-zoom detail require separate evidence.</p><p>Only reviewed REFERENCE points from the API are displayed. No INTAKE/MGMT coordinates, canonical geometry, local GLB-to-WGS84 transform, canal lines or inferred asset positions are added. The initial camera uses registry context metadata and is not a surveyed reservoir extent.</p><p>The operator map is linked for consultation; no right to copy or rehost it was established. <a href={OPERATOR_MAP_URL} target="_blank" rel="noreferrer">Operator map source ↗</a> · <a href="https://siwrp.org.vn/news/ban-do_520.html" target="_blank" rel="noreferrer">SIWRP map catalogue ↗</a>. Their publications are not layers in this map.</p></details>
    </PanelSection>
  </section>;
}

"use client";
import { documentHref } from "@/lib/document-navigation";
import { mapView, readView, saveView, viewStorage } from "@/lib/workspace-view-state";
import { observeCanvasResize } from "@/lib/workspace-layout";
import { satelliteConfig, STREET_LAYER } from "@/lib/satellite-provider";
import { AssetSymbol } from "@/components/asset/asset-symbol";
import { assetSymbolSvg, assetSymbols } from "@/lib/asset-symbol";
import { assetDisplayName } from "@/lib/asset-display";
import { useEffect, useRef, useState } from "react";
import type {
  Map as LibreMap,
  Popup as LibrePopup,
  LngLatLike,
} from "maplibre-gl";
import type { ExplorerRecords } from "@/lib/explorer-data";
import { assetLocation, mapGeometry, locationLayer, pointGroups, pointNeighbors } from "@/lib/asset-location";
import { locationEvidence } from "@/lib/location-evidence";
import { geometryPositions } from "@/lib/asset-geometry";
import type { Asset } from "@/types/asset";
import type { Reservoir } from "@/types/reservoir";

const basemapConfig = satelliteConfig({ provider: "maptiler", maptilerKey: process.env.NEXT_PUBLIC_MAPTILER_KEY });
const emptyRecords: ExplorerRecords = {};
const ignoreSelection = () => {};
const LAYERS = [
  "asset-points",
  "asset-lines",
  "asset-polygon-outlines",
  "asset-polygons",
];
export function AssetMap({
  reservoir,
  assets, selectedId, onSelect = ignoreSelection, records = emptyRecords, contextVisible = true,
}: {
  reservoir: Reservoir;
  assets: Asset[];
  selectedId?: string;
  onSelect?: (asset: Asset) => void;
  records?: ExplorerRecords;
  contextVisible?: boolean;
}) {
  const selection = useRef({ selectedId, onSelect });
  useEffect(() => { selection.current = { selectedId, onSelect }; }, [selectedId, onSelect]);
  const highlight = useRef<((id?: string) => void) | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const resetView = useRef<(() => void) | null>(null);
  const selectAsset = useRef<((asset: Asset) => void) | null>(null);
  const retryBasemap = useRef<(() => void) | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [basemapUnavailable, setBasemapUnavailable] = useState(false);
  const [locationUnavailable, setLocationUnavailable] = useState(false);
  const [mapState, setMapState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const selected = assets.find(asset => asset.id === selectedId);
  const mapped = assets.filter((asset) => mapGeometry(asset) !== null);
  const assetsJson = JSON.stringify(assets);
  useEffect(() => {
    const assets: Asset[] = JSON.parse(assetsJson);
    let disposed = false;
    let map: LibreMap | undefined;
    let stopResize: (() => void) | undefined;
    let popup: LibrePopup | undefined;
    const symbolButtons = new Map<string, HTMLButtonElement>();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let basemapTimer: ReturnType<typeof setTimeout> | undefined;
    const viewKey = () => `asset-map:${reservoir.id}:${selection.current.selectedId ?? "overview"}`;
    const remember = () => {
      if (!map) return;
      const center = map.getCenter();
      saveView(viewStorage(), viewKey(), { center: [center.lng, center.lat], zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch() });
    };
    void import("maplibre-gl")
      .then(({ Map, Popup, NavigationControl, AttributionControl, ScaleControl, Marker, LngLatBounds, setWorkerUrl }) => {
        if (disposed || !container.current) return;
        setMapState("loading");
        setBasemapUnavailable(false);
        setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
        const instance = new Map({
          container: container.current,
          // Local style loads independently of the optional raster basemap.
          style: { version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": "#eaf0ec" } }] },
          attributionControl: false,
          center: [reservoir.longitude, reservoir.latitude],
          zoom: 10,
        });
        map = instance;
        instance.on("moveend", remember);
        stopResize = observeCanvasResize(container.current, () => instance.resize());
        resetView.current = () => instance.flyTo({ center: [reservoir.longitude, reservoir.latitude], zoom: 10 });
        instance.addControl(new NavigationControl(), "top-right");
        instance.addControl(new AttributionControl({ compact: false }), "bottom-right");
        instance.addControl(new ScaleControl({ unit: "metric" }), "bottom-left");
        // Switch only the background source; asset layers, popups and camera survive.
        let basemapId: string | null = null;
        let basemapRevision = 0;
        let basemapProvider: "maptiler" | "osm" = "osm";
        let providerLogo: { onAdd: () => HTMLElement; onRemove: () => void } | undefined;
        const removeBasemap = () => {
          if (basemapTimer) clearTimeout(basemapTimer);
          const previous = basemapId;
          basemapId = null; // Ignore late source events from the removed attempt.
          if (previous && instance.getLayer(previous)) instance.removeLayer(previous);
          if (previous && instance.getSource(previous)) instance.removeSource(previous);
          if (providerLogo) { instance.removeControl(providerLogo); providerLogo = undefined; }
        };
        const failBasemap = () => {
          if (disposed || !basemapId) return;
          const fallback = basemapProvider === "maptiler";
          removeBasemap();
          if (fallback) startBasemap("osm");
          else setBasemapUnavailable(true);
        };
        const startBasemap = (provider: "maptiler" | "osm") => {
          if (disposed) return;
          removeBasemap();
          setBasemapUnavailable(false);
          basemapProvider = provider;
          const id = `asset-basemap-${++basemapRevision}`;
          basemapId = id;
          instance.addSource(id, provider === "maptiler" && basemapConfig.status === "CONFIGURED"
            ? { type: "raster", url: `https://api.maptiler.com/maps/streets/256/tiles.json?key=${encodeURIComponent(basemapConfig.key)}`, tileSize: 256,
                attribution: '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> | ' + STREET_LAYER.attribution }
            : { type: "raster", tiles: STREET_LAYER.tiles, tileSize: STREET_LAYER.tileSize, maxzoom: STREET_LAYER.maxzoom, attribution: STREET_LAYER.attribution });
          instance.addLayer({ id, type: "raster", source: id }, instance.getLayer("reservoir-context") ? "reservoir-context" : undefined);
          if (provider === "maptiler") {
            const logo = document.createElement("a"); logo.className = "maplibregl-ctrl observation-provider-logo";
            logo.href = "https://www.maptiler.com/"; logo.target = "_blank"; logo.rel = "noreferrer";
            const image = document.createElement("img"); image.src = "https://api.maptiler.com/resources/logo.svg"; image.alt = "MapTiler logo"; image.width = 88;
            logo.append(image);
            providerLogo = { onAdd: () => logo, onRemove: () => logo.remove() };
            instance.addControl(providerLogo, "bottom-right");
          }
          basemapTimer = setTimeout(() => { if (basemapId === id) failBasemap(); }, 15000);
        };
        retryBasemap.current = () => startBasemap(basemapConfig.status === "CONFIGURED" ? "maptiler" : "osm");
        instance.on("sourcedata", event => {
          if (!disposed && event.sourceId === basemapId && event.isSourceLoaded) {
            if (basemapTimer) clearTimeout(basemapTimer);
            setBasemapUnavailable(false);
          }
        });
        instance.on("error", event => {
          if (disposed) return;
          if ("sourceId" in event && typeof event.sourceId === "string" && event.sourceId.startsWith("asset-basemap-")) {
            if (event.sourceId === basemapId) failBasemap();
          } else setMapState("error");
        });
        timer = setTimeout(() => {
          if (!disposed && !instance.loaded()) setMapState("error");
        }, 15000);
        const features = assets.flatMap((asset) =>
          mapGeometry(asset)
            ? [
                {
                  type: "Feature" as const,
                  id: asset.id,
                  geometry: mapGeometry(asset)!,
                  properties: {
                    id: asset.id,
                    asset_code: asset.asset_code,
                    name: asset.name,
                    category: asset.category.code,
                    data_status: asset.data_status,
                    location_status: assetLocation(asset).location_status,
                    layer_kind: locationLayer(asset),
                  },
                },
              ]
            : [],
        );
        // A camera overview around the registry center is context, not a claimed reservoir extent.
        const fitContext = () => instance.jumpTo({ center: [reservoir.longitude, reservoir.latitude], zoom: 10 });
        const showPopup = (asset: Asset, coordinate: LngLatLike) => {
          popup?.remove();
          const content = document.createElement("div");
          content.className = "reservoir-popup asset-popup";
          const title = document.createElement("h3");
          title.className = "asset-display-name";
          title.textContent = assetDisplayName(asset);
          content.append(title);
          for (const value of [

            `Category: ${asset.category.name}`,
            `${asset.data_status} · ${assetLocation(asset).location_status.replaceAll("_", " ")}`,
            assetLocation(asset).location_status === "REFERENCE_LOCATION" ? "Reference only — not surveyed geometry" : `Geometry: ${mapGeometry(asset)?.type ?? "Unavailable"}`,
          ]) {
            const line = document.createElement("p");
            line.textContent = value;
            content.append(line);
          }
          const location = assetLocation(asset);
          const evidence = locationEvidence(asset);
          for (const [key, value] of evidence.fields) {
            const line = document.createElement("p"); line.textContent = `${key}: ${value}`; content.append(line);
          }
          if (evidence.href) {
            const source = document.createElement("a");
            source.textContent = `Open source${evidence.page ? ` · PDF page ${evidence.page}` : ""} →`;
            source.href = evidence.href.startsWith("/") ? documentHref(evidence.href, window.location.pathname + window.location.search + window.location.hash) : evidence.href;
            if (!evidence.href.startsWith("/")) { source.target = "_blank"; source.rel = "noopener noreferrer"; }
            content.append(source);
          }
          const neighbors = pointNeighbors(assets, asset.id, point => instance.project(point));
          if (neighbors.length > 1) {
            const label = document.createElement("p"); label.textContent = "Nearby / shared reference points · Select the exact asset"; content.append(label);
            for (const neighbor of neighbors) {
              const choice = document.createElement("button"); choice.type = "button"; choice.className = "text-link";
              choice.textContent = assetDisplayName(neighbor); choice.setAttribute("aria-pressed", String(neighbor.id === asset.id));
              choice.addEventListener("click", () => { selection.current.onSelect(neighbor); selectAsset.current?.(neighbor); });
              content.append(choice);
            }
          }
          const metadata = document.createElement("details"); const summary = document.createElement("summary"); summary.textContent = "Technical details"; metadata.append(summary);
          for (const [key,value] of Object.entries({"Asset code":asset.asset_code,UUID:asset.id,Source:location.source,Locator:location.locator,CRS:location.crs,"Evidence ID":location.evidence_id,Limitation:location.accuracy_limitation})) {
            if (!value) continue; const line=document.createElement("p");line.textContent=`${key}: ${value}`;metadata.append(line);
          }
          content.append(metadata);
          const link = document.createElement("a");
          link.textContent = "View Asset →";
          link.href = documentHref(`/assets/${encodeURIComponent(asset.id)}`, window.location.pathname + window.location.search + window.location.hash);
          content.append(link);
          if (selection.current.onSelect !== ignoreSelection) {
            const openPanel = document.createElement("button");
            openPanel.className = "text-link";
            openPanel.textContent = "Open Panel →";
            openPanel.addEventListener("click", () => {
              selection.current.onSelect(asset);
              requestAnimationFrame(() => document.getElementById("selected-asset-panel")?.focus());
            });
            content.append(openPanel);
          }
          for (const record of (records[asset.id]?.technical ?? []).slice(0, 2)) {
            const line = document.createElement("p");
            line.textContent = `${record.attribute_label}: ${record.value_number ?? record.value_text ?? "Unavailable"} ${record.unit ?? ""} · ${record.reviewed_provenance?.verification_level ?? record.verification_status}`;
            content.append(line);
          }
          popup = new Popup({ maxWidth: "min(380px, calc(100vw - 60px))", offset: 20, anchor: "left", focusAfterOpen: false })
            .setLngLat(coordinate)
            .setDOMContent(content)
            .addTo(instance);
        };
        instance.on("load", () => {
          if (disposed) return;
          retryBasemap.current?.();
          instance.addSource("reservoir-context", {
            type: "geojson",
            data: { type: "FeatureCollection", features: contextVisible ? [{ type: "Feature", geometry: { type: "Point", coordinates: [reservoir.longitude, reservoir.latitude] }, properties: {} }] : [] },
          });
          instance.addLayer({ id: "reservoir-context", type: "circle", source: "reservoir-context", paint: { "circle-radius": 11, "circle-color": "#ffffff", "circle-opacity": 0.5, "circle-stroke-width": 2, "circle-stroke-color": "#64748b" } });
          if (contextVisible) {
            const label = document.createElement("div");
            label.className = "reservoir-context-label";
            label.textContent = `${reservoir.name} · Context only`;
            new Marker({ element: label, anchor: "bottom", offset: [0, -15] }).setLngLat([reservoir.longitude, reservoir.latitude]).addTo(instance);
          }
          instance.addSource("assets", {
            type: "geojson",
            promoteId: "id",
            data: { type: "FeatureCollection", features },
          });
          instance.addLayer({
            id: "asset-polygons",
            type: "fill",
            source: "assets",
            filter: ["==", ["geometry-type"], "Polygon"],
            paint: { "fill-color": ["case", ["boolean", ["feature-state", "selected"], false], "#059669", ["match", ["get", "layer_kind"], "RS_VERIFIED", "#2563eb", "RS_REFERENCE", "#c77713", "DEV", "#8055ad", "#64748b"]], "fill-opacity": 0.3 },
          });
          instance.addLayer({
            id: "asset-polygon-outlines",
            type: "line",
            source: "assets",
            filter: ["==", ["geometry-type"], "Polygon"],
            paint: { "line-color": ["case", ["boolean", ["feature-state", "selected"], false], "#059669", ["match", ["get", "layer_kind"], "RS_VERIFIED", "#2563eb", "RS_REFERENCE", "#c77713", "DEV", "#8055ad", "#64748b"]], "line-width": 2 },
          });
          instance.addLayer({
            id: "asset-lines",
            type: "line",
            source: "assets",
            filter: ["==", ["geometry-type"], "LineString"],
            paint: { "line-color": ["case", ["boolean", ["feature-state", "selected"], false], "#059669", ["match", ["get", "layer_kind"], "RS_VERIFIED", "#2563eb", "RS_REFERENCE", "#c77713", "DEV", "#8055ad", "#64748b"]], "line-width": 5 },
          });
          instance.addLayer({
            id: "asset-points",
            type: "circle",
            source: "assets",
            filter: ["==", ["geometry-type"], "Point"],
            paint: {
              "circle-color": ["case", ["boolean", ["feature-state", "selected"], false], "#059669", ["match", ["get", "layer_kind"], "RS_VERIFIED", "#2563eb", "RS_REFERENCE", "#c77713", "DEV", "#8055ad", "#64748b"]],
              "circle-radius": ["case", ["boolean", ["feature-state", "selected"], false], 12, 9],
              "circle-opacity": ["case", ["==", ["get", "layer_kind"], "RS_REFERENCE"], 0, 1],
              "circle-stroke-width": 3,
              "circle-stroke-color": ["case", ["boolean", ["feature-state", "selected"], false], "#047857", ["match", ["get", "layer_kind"], "RS_VERIFIED", "#2563eb", "RS_REFERENCE", "#c77713", "DEV", "#8055ad", "#64748b"]],
            },
          });
          const originalLayers = instance.getStyle().layers.filter(layer => (layer.type === "fill" || layer.type === "line" || layer.type === "circle") && LAYERS.includes(layer.id));
          for (const layer of originalLayers) instance.removeLayer(layer.id);
          const interactiveLayers: string[] = [];
          for (const kind of ["DEV", "OTHER", "RS_VERIFIED", "RS_REFERENCE"]) {
            for (const layer of originalLayers) {
              if (!(layer.type === "fill" || layer.type === "line" || layer.type === "circle")) continue;
              const id = `${kind}-${layer.id}`;
              instance.addLayer({ ...layer, id, filter: ["all", ["==", ["geometry-type"], layer.id === "asset-points" ? "Point" : layer.id === "asset-lines" ? "LineString" : "Polygon"], ["==", ["get", "layer_kind"], kind]] });
              interactiveLayers.push(id);
            }
          }
          instance.addLayer({ id: "selected-halo", type: "circle", source: "assets", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 18, "circle-opacity": 0, "circle-stroke-width": 3, "circle-stroke-color": "#047857", "circle-stroke-opacity": ["case", ["boolean", ["feature-state", "selected"], false], 1, 0] } });
          for (const geometryType of ["LineString", "Polygon"]) instance.addLayer({ id: `selected-${geometryType}`, type: "line", source: "assets", filter: ["==", ["geometry-type"], geometryType], paint: { "line-width": 6, "line-color": "#047857", "line-opacity": ["case", ["boolean", ["feature-state", "selected"], false], 1, 0] } });
          for (const group of pointGroups(assets)) {
            const asset = group[0], coordinate = geometryPositions(mapGeometry(asset)!)[0];
            const reference = assetLocation(asset).location_status === "REFERENCE_LOCATION";
            const button = document.createElement("button");
            button.type = "button";
            button.className = `asset-map-symbol ${reference ? "is-reference" : "is-geometry"} ${locationLayer(asset) === "DEV" ? "is-dev" : ""}`;
            button.innerHTML = assetSymbolSvg(asset.category.code);
            button.setAttribute("aria-label", group.length > 1 ? `Select shared location · ${group.map(assetDisplayName).join("; ")}` : `Select ${reference ? "reference location" : "geometry"} ${assetDisplayName(asset)}`);
            button.dataset.assetIds = JSON.stringify(group.map(item => item.id));
            if (reference || group.length > 1) { const label=document.createElement("span"); label.textContent=group.length > 1 ? `${group.length} assets` : "Reference"; button.append(label); }
            button.addEventListener("click", event => {
              event.stopPropagation();
              if (group.length === 1) { selection.current.onSelect(asset); selectAsset.current?.(asset); return; }
              popup?.remove();
              const choices = document.createElement("div"); choices.className = "asset-popup";
              const heading = document.createElement("strong"); heading.textContent = "Shared location · Choose an asset"; choices.append(heading);
              const warning = document.createElement("p"); warning.textContent = "Reference only — not surveyed geometry. Source coordinates are unchanged."; choices.append(warning);
              for (const item of group) {
                const choice = document.createElement("button"); choice.type = "button"; choice.className = "text-link"; choice.textContent = assetDisplayName(item);
                choice.addEventListener("click", () => { selection.current.onSelect(item); selectAsset.current?.(item); }); choices.append(choice);
              }
              popup = new Popup({ maxWidth:"min(380px, calc(100vw - 60px))", focusAfterOpen:false }).setLngLat(coordinate).setDOMContent(choices).addTo(instance);
            });
            for (const item of group) symbolButtons.set(item.id, button);
            new Marker({ element: button }).setLngLat(coordinate).addTo(instance);
          }
          instance.on("click", (event) => {
            const hit = instance.queryRenderedFeatures(event.point, {
              layers: interactiveLayers,
            })[0];
            const asset = assets.find((item) => item.id === hit?.properties.id);
            if (asset) { selection.current.onSelect(asset); selectAsset.current?.(asset); }
          });
          instance.on("mousemove", (event) => {
            instance.getCanvas().style.cursor = instance.queryRenderedFeatures(
              event.point,
              { layers: interactiveLayers },
            ).length
              ? "pointer"
              : "";
          });
          selectAsset.current = (asset) => {
            const geometry = mapGeometry(asset);
            if (!geometry) { popup?.remove(); setLocationUnavailable(true); fitContext(); return; }
            setLocationUnavailable(false);
            const assetBounds = new LngLatBounds();
            for (const position of geometryPositions(geometry))
              assetBounds.extend(position);
            const center = assetBounds.getCenter();
            instance.fitBounds(assetBounds, {
              padding: { top: 60, bottom: 70, left: 60, right: Math.min(380, instance.getContainer().clientWidth * 0.45) },
              maxZoom: assetLocation(asset).location_status === "REFERENCE_LOCATION" ? 11 : 14,
              duration: 0,
            });
            showPopup(asset, center);
          };
          highlight.current = (id) => {
            for (const button of new Set(symbolButtons.values())) { const selected = (JSON.parse(button.dataset.assetIds ?? "[]") as string[]).includes(id ?? ""); button.classList.toggle("is-selected", selected); button.setAttribute("aria-pressed", String(selected)); }
            for (const asset of assets) instance.setFeatureState({ source: "assets", id: asset.id }, { selected: asset.id === id });
            const asset = assets.find(a => a.id === id);
            popup?.remove();
            if (asset) selectAsset.current?.(asset);
            else { setLocationUnavailable(false); fitContext(); }
          };
          const remembered = readView(viewStorage(), viewKey(), mapView);
          highlight.current(selection.current.selectedId);
          if (remembered) instance.jumpTo(remembered);
          if (timer) clearTimeout(timer);
          setMapState("ready");
        });
      })
      .catch(() => {
        if (!disposed) setMapState("error");
      });
    return () => {
      remember();
      disposed = true;
      selectAsset.current = null;
      highlight.current = null;
      if (timer) clearTimeout(timer);
      if (basemapTimer) clearTimeout(basemapTimer);
      popup?.remove();
      stopResize?.();
      resetView.current = null;
      retryBasemap.current = null;
      map?.remove();
    };
  }, [reservoir, assetsJson, records, contextVisible, attempt]);
  useEffect(() => { highlight.current?.(selectedId); }, [selectedId]);
  return (
    <div>
      <div className="map-frame asset-map-frame">
        <button className="map-reset" onClick={() => resetView.current?.()} disabled={mapState !== "ready"}>Reset map</button>
        <div
          ref={container}
          className="asset-map-canvas"
          aria-label={`Asset geometry map for ${reservoir.name}`}
        />
        <div className="map-context-heading">{reservoir.name}<span>Basemap / registry center · Context only</span></div>
        {basemapUnavailable && <p className="basemap-notice" role="status">Basemap unavailable. <button className="text-link" onClick={() => retryBasemap.current?.()}>Retry basemap</button></p>}
        {mapState === "loading" && (
          <p className="map-notice" role="status">
            Loading asset map…
          </p>
        )}
        {mapState === "error" && (
          <div className="map-notice" role="alert">
            <p>The map could not load completely. Check the connection and WebGL support. Asset records remain available in the panel.</p>
            <button className="text-link" onClick={() => setAttempt(value => value + 1)}>Retry map</button>
          </div>
        )}
        <details
          className="map-legend asset-legend"
          aria-label="Asset geometry legend"
        >
          <summary>Map legend</summary><p className="eyebrow">Asset symbols</p><div className="symbol-legend">{Object.entries(assetSymbols).map(([code,symbol]) => <span key={code}><AssetSymbol category={code}/>{symbol.label}</span>)}</div>
          <p className="eyebrow">Location layers</p>
          <div><span className="status-dot" style={{ background: "#2563eb" }} />RS verified geometry</div>
          <div><span className="status-dot reference-dot" />RS reference location</div>
          <div><span className="status-dot context-dot" />Context only{!contextVisible ? " (hidden)" : ""}</div>
          <div><span className="status-dot context-dot" />Candidates / no location · No pin</div>
          <div><span className="status-dot" style={{ background: "#059669" }} />Selected asset</div>
        </details>
      </div>
      {locationUnavailable && <p className="location-unavailable" role="status">{selected ? (assetLocation(selected).reason ?? "No accepted location for this asset.") : "No accepted location for this asset."} Candidate coordinates are not displayed.</p>}
      {assets.length === 0 ? (
        <p className="muted mt-3">
          No asset locations match the filters. Reservoir context is navigation only.
        </p>
      ) : mapped.length === 0 ? (
        <p className="muted mt-3" role="status">
          NO LOCATION · No asset-specific location available in this view. Asset identities remain accessible in the registry. Reservoir context is not asset location evidence.
        </p>
      ) : (
        <>
          <p className="muted mt-3 text-sm">
            {mapped.length} of {assets.length} assets have display locations. Reference locations are navigation / presentation only, not verified GIS evidence.
            {mapped.length < assets.length &&
              ` ${assets.length - mapped.length} asset(s) without accepted locations remain in the explorer.`}
          </p>
          <div
            className="asset-locate-controls"
            aria-label="Locate an asset on the map"
          >
            {mapped.map((asset) => (
              <button
                key={asset.id}
                className="locate-button"
                disabled={mapState !== "ready"}
                onClick={() => { onSelect(asset); selectAsset.current?.(asset); }}
              >
                Locate {assetDisplayName(asset)}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

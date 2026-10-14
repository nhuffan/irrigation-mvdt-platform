"use client";
import { assetDisplayName, locationSourceTitle } from "@/lib/asset-display";
import { useEffect, useRef, useState } from "react";
import type {
  Map as LibreMap,
  Popup as LibrePopup,
  LngLatLike,
} from "maplibre-gl";
import type { ExplorerRecords } from "@/lib/explorer-data";
import { assetLocation, mapGeometry, locationLayer } from "@/lib/asset-location";
import { geometryPositions } from "@/lib/asset-geometry";
import type { Asset } from "@/types/asset";
import type { Reservoir } from "@/types/reservoir";

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
  const selectAsset = useRef<((asset: Asset) => void) | null>(null);
  const [basemapUnavailable, setBasemapUnavailable] = useState(false);
  const [locationUnavailable, setLocationUnavailable] = useState(false);
  const [mapState, setMapState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const mapped = assets.filter((asset) => mapGeometry(asset) !== null);
  const assetsJson = JSON.stringify(assets);
  useEffect(() => {
    const assets: Asset[] = JSON.parse(assetsJson);
    let disposed = false;
    let map: LibreMap | undefined;
    let popup: LibrePopup | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let basemapTimer: ReturnType<typeof setTimeout> | undefined;
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
        instance.addControl(new NavigationControl(), "top-right");
        instance.addControl(new AttributionControl({ compact: false }), "bottom-right");
        instance.addControl(new ScaleControl({ unit: "metric" }), "bottom-left");
        instance.on("error", (event) => {
          if (disposed) return;
          if ("sourceId" in event && event.sourceId === "basemap") setBasemapUnavailable(true);
          else setMapState("error");
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
          title.textContent = assetDisplayName(asset);
          content.append(title);
          for (const value of [

            `Category: ${asset.category.name}`,
            `${asset.data_status} · ${assetLocation(asset).location_status.replaceAll("_", " ")}`,
            locationLayer(asset) === "DEV" ? "DEV example — not research evidence" : assetLocation(asset).location_status === "REFERENCE_LOCATION" ? "Map-symbol reference location only. Not surveyed geometry." : `Geometry: ${mapGeometry(asset)?.type ?? "Unavailable"}`,
          ]) {
            const line = document.createElement("p");
            line.textContent = value;
            content.append(line);
          }
          const location = assetLocation(asset);
          if (location.location_status === "REFERENCE_LOCATION") {
            const source = document.createElement("p"); source.textContent = locationSourceTitle(location.source); content.append(source);
            const scale = location.accuracy_limitation.match(/1:[\d,]+/)?.[0];
            if (scale) { const line = document.createElement("p"); line.textContent = `Map scale · ${scale}`; content.append(line); }
          }
          const metadata = document.createElement("details"); const summary = document.createElement("summary"); summary.textContent = "Technical details"; metadata.append(summary);
          for (const [key,value] of Object.entries({"Asset code":asset.asset_code,UUID:asset.id,Source:location.source,Locator:location.locator,CRS:location.crs,"Evidence ID":location.evidence_id,Limitation:location.accuracy_limitation})) {
            if (!value) continue; const line=document.createElement("p");line.textContent=`${key}: ${value}`;metadata.append(line);
          }
          content.append(metadata);
          const link = document.createElement("a");
          link.textContent = "View Asset →";
          link.href = `/assets/${encodeURIComponent(asset.id)}`;
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
          popup = new Popup({ maxWidth: "320px", offset: 20, anchor: "left", focusAfterOpen: false })
            .setLngLat(coordinate)
            .setDOMContent(content)
            .addTo(instance);
        };
        instance.on("load", () => {
          if (disposed) return;
          instance.addSource("basemap", { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' });
          instance.addLayer({ id: "basemap", type: "raster", source: "basemap" });
          basemapTimer = setTimeout(() => {
            if (!disposed && !instance.isSourceLoaded("basemap")) setBasemapUnavailable(true);
          }, 15000);
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
          for (const asset of assets.filter(a => mapGeometry(a)?.type === "Point" && assetLocation(a).location_status === "REFERENCE_LOCATION" && locationLayer(a) !== "DEV")) {
            const label = document.createElement("button"); label.className = "reference-map-label"; label.textContent = "REFERENCE";
            label.setAttribute("aria-label", `Select reference location ${assetDisplayName(asset)}`);
            label.addEventListener("click", (event) => { event.stopPropagation(); selection.current.onSelect(asset); selectAsset.current?.(asset); });
            new Marker({ element: label, anchor: "top", offset: [0, 21] }).setLngLat(geometryPositions(mapGeometry(asset)!)[0]).addTo(instance);
          }
          instance.on("click", (event) => {
            const hit = instance.queryRenderedFeatures(event.point, {
              layers: interactiveLayers,
            })[0];
            const asset = assets.find((item) => item.id === hit?.properties.id);
            if (asset) { selection.current.onSelect(asset); showPopup(asset, event.lngLat); }
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
            if (!geometry) { setLocationUnavailable(true); fitContext(); return; }
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
            for (const asset of assets) instance.setFeatureState({ source: "assets", id: asset.id }, { selected: asset.id === id });
            const asset = assets.find(a => a.id === id);
            popup?.remove();
            if (asset) selectAsset.current?.(asset);
            else { setLocationUnavailable(false); fitContext(); }
          };
          highlight.current(selection.current.selectedId);
          if (timer) clearTimeout(timer);
          setMapState("ready");
        });
      })
      .catch(() => {
        if (!disposed) setMapState("error");
      });
    return () => {
      disposed = true;
      selectAsset.current = null;
      highlight.current = null;
      if (timer) clearTimeout(timer);
      if (basemapTimer) clearTimeout(basemapTimer);
      popup?.remove();
      map?.remove();
    };
  }, [reservoir, assetsJson, records, contextVisible]);
  useEffect(() => { highlight.current?.(selectedId); }, [selectedId]);
  return (
    <div>
      <div className="map-frame asset-map-frame">
        <div
          ref={container}
          className="asset-map-canvas"
          aria-label={`Asset geometry map for ${reservoir.name}`}
        />
        <div className="map-context-heading">{reservoir.name}<span>Basemap / registry center · Context only</span></div>
        {basemapUnavailable && <p className="basemap-notice" role="status">Basemap unavailable · Asset locations and panel remain available.</p>}
        {mapState === "loading" && (
          <p className="map-notice" role="status">
            Loading asset map…
          </p>
        )}
        {mapState === "error" && (
          <p className="map-notice" role="alert">
            The map could not load completely. Check your connection and WebGL
            support, then reload. Asset records remain available below.
          </p>
        )}
        <aside
          className="map-legend asset-legend"
          aria-label="Asset geometry legend"
        >
          <p className="eyebrow">Location layers</p>
          <div><span className="status-dot" style={{ background: "#2563eb" }} />RS verified geometry</div>
          <div><span className="status-dot reference-dot" />RS reference location</div>
          <div><span className="status-dot" style={{ background: "#8055ad" }} />DEV geometry</div>
          <div><span className="status-dot context-dot" />Context only{!contextVisible ? " (hidden)" : ""}</div>
          <div><span className="status-dot context-dot" />NO LOCATION · registry only</div>
          <div><span className="status-dot" style={{ background: "#059669" }} />Selected asset</div>
        </aside>
      </div>
      {locationUnavailable && <p className="location-unavailable" role="status">Location unavailable for this asset · Showing reservoir context only.</p>}
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
              ` ${assets.length - mapped.length} asset(s) with NO LOCATION remain in the registry.`}
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

"use client";
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
    void import("maplibre-gl")
      .then(({ Map, Popup, NavigationControl, LngLatBounds, setWorkerUrl }) => {
        if (disposed || !container.current) return;
        setMapState("loading");
        setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
        const instance = new Map({
          container: container.current,
          style: "https://demotiles.maplibre.org/style.json",
          center: [reservoir.longitude, reservoir.latitude],
          zoom: 9,
        });
        map = instance;
        instance.addControl(new NavigationControl(), "top-right");
        instance.on("error", () => {
          if (!disposed) setMapState("error");
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
        const bounds = new LngLatBounds();
        for (const feature of features)
          for (const position of geometryPositions(feature.geometry))
            bounds.extend(position);
        if (!bounds.isEmpty())
          instance.fitBounds(bounds, { padding: 70, maxZoom: 15, duration: 0 });
        const showPopup = (asset: Asset, coordinate: LngLatLike) => {
          popup?.remove();
          const content = document.createElement("div");
          content.className = "reservoir-popup asset-popup";
          const title = document.createElement("h3");
          title.textContent = asset.name;
          content.append(title);
          for (const value of [
            asset.asset_code,
            `Category: ${asset.category.name}`,
            `${asset.data_status} · ${assetLocation(asset).location_status.replaceAll("_", " ")}`,
            locationLayer(asset) === "DEV" ? "DEV example — not research evidence" : assetLocation(asset).location_status === "REFERENCE_LOCATION" ? "Navigation / presentation only. Not verified GIS evidence." : `Geometry: ${mapGeometry(asset)?.type ?? "Unavailable"}`,
          ]) {
            const line = document.createElement("p");
            line.textContent = value;
            content.append(line);
          }
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
          popup = new Popup({ maxWidth: "300px", offset: 12, anchor: "bottom", focusAfterOpen: false })
            .setLngLat(coordinate)
            .setDOMContent(content)
            .addTo(instance);
        };
        instance.on("load", () => {
          if (disposed) return;
          instance.addSource("reservoir-context", {
            type: "geojson",
            data: { type: "FeatureCollection", features: contextVisible ? [{ type: "Feature", geometry: { type: "Point", coordinates: [reservoir.longitude, reservoir.latitude] }, properties: {} }] : [] },
          });
          instance.addLayer({ id: "reservoir-context", type: "circle", source: "reservoir-context", paint: { "circle-radius": 11, "circle-color": "#ffffff", "circle-opacity": 0.5, "circle-stroke-width": 2, "circle-stroke-color": "#64748b" } });
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
              "circle-opacity": ["case", ["==", ["get", "layer_kind"], "RS_REFERENCE"], 0.4, 1],
              "circle-stroke-width": 3,
              "circle-stroke-color": ["case", ["boolean", ["feature-state", "selected"], false], "#047857", ["match", ["get", "layer_kind"], "RS_VERIFIED", "#2563eb", "RS_REFERENCE", "#c77713", "DEV", "#8055ad", "#64748b"]],
            },
          });
          instance.on("click", (event) => {
            const hit = instance.queryRenderedFeatures(event.point, {
              layers: LAYERS,
            })[0];
            const asset = assets.find((item) => item.id === hit?.properties.id);
            if (asset) { selection.current.onSelect(asset); showPopup(asset, event.lngLat); }
          });
          instance.on("mousemove", (event) => {
            instance.getCanvas().style.cursor = instance.queryRenderedFeatures(
              event.point,
              { layers: LAYERS },
            ).length
              ? "pointer"
              : "";
          });
          selectAsset.current = (asset) => {
            const geometry = mapGeometry(asset);
            if (!geometry) return;
            const assetBounds = new LngLatBounds();
            for (const position of geometryPositions(geometry))
              assetBounds.extend(position);
            const center = assetBounds.getCenter();
            instance.fitBounds(assetBounds, {
              padding: { top: Math.min(260, instance.getContainer().clientHeight * 0.55), bottom: 50, left: 70, right: 70 },
              maxZoom: 15,
              duration: 0,
            });
            showPopup(asset, center);
          };
          highlight.current = (id) => {
            for (const asset of assets) instance.setFeatureState({ source: "assets", id: asset.id }, { selected: asset.id === id });
            const asset = assets.find(a => a.id === id);
            popup?.remove();
            if (asset && mapGeometry(asset)) selectAsset.current?.(asset);
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
          <div><span className="status-dot context-dot" />Reservoir context{!contextVisible ? " (hidden)" : ""}</div>
          <div><span className="status-dot" style={{ background: "#059669" }} />Selected asset</div>
        </aside>
      </div>
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
                Locate {asset.asset_code}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

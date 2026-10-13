"use client";
import { useEffect, useRef, useState } from "react";
import type {
  Map as LibreMap,
  Popup as LibrePopup,
  LngLatLike,
} from "maplibre-gl";
import type { ExplorerRecords } from "@/lib/explorer-data";
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
  assets, selectedId, onSelect = ignoreSelection, records = emptyRecords,
}: {
  reservoir: Reservoir;
  assets: Asset[];
  selectedId?: string;
  onSelect?: (asset: Asset) => void;
  records?: ExplorerRecords;
}) {
  const selection = useRef({ selectedId, onSelect });
  useEffect(() => { selection.current = { selectedId, onSelect }; }, [selectedId, onSelect]);
  const highlight = useRef<((id?: string) => void) | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const selectAsset = useRef<((asset: Asset) => void) | null>(null);
  const [mapState, setMapState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const mapped = assets.filter((asset) => asset.geometry !== null);
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
          asset.geometry
            ? [
                {
                  type: "Feature" as const,
                  id: asset.id,
                  geometry: asset.geometry,
                  properties: {
                    id: asset.id,
                    asset_code: asset.asset_code,
                    name: asset.name,
                    category: asset.category.code,
                    data_status: asset.data_status,
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
            `${asset.data_status} · Geometry: ${asset.geometry?.type ?? "Unavailable"}`,
          ]) {
            const line = document.createElement("p");
            line.textContent = value;
            content.append(line);
          }
          const link = document.createElement("a");
          link.textContent = "View Asset →";
          link.href = `/assets/${encodeURIComponent(asset.id)}`;
          content.append(link);
          for (const record of (records[asset.id]?.technical ?? []).slice(0, 2)) {
            const line = document.createElement("p");
            line.textContent = `${record.attribute_label}: ${record.value_number ?? record.value_text ?? "Unavailable"} ${record.unit ?? ""} · ${record.reviewed_provenance?.verification_level ?? record.verification_status}`;
            content.append(line);
          }
          popup = new Popup({ maxWidth: "300px", offset: 12, anchor: "bottom" })
            .setLngLat(coordinate)
            .setDOMContent(content)
            .addTo(instance);
        };
        instance.on("load", () => {
          if (disposed) return;
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
            paint: { "fill-color": ["case", ["boolean", ["feature-state", "selected"], false], "#059669", "#7c3aed"], "fill-opacity": 0.3 },
          });
          instance.addLayer({
            id: "asset-polygon-outlines",
            type: "line",
            source: "assets",
            filter: ["==", ["geometry-type"], "Polygon"],
            paint: { "line-color": ["case", ["boolean", ["feature-state", "selected"], false], "#059669", "#6d28d9"], "line-width": 2 },
          });
          instance.addLayer({
            id: "asset-lines",
            type: "line",
            source: "assets",
            filter: ["==", ["geometry-type"], "LineString"],
            paint: { "line-color": ["case", ["boolean", ["feature-state", "selected"], false], "#059669", "#0369a1"], "line-width": 5 },
          });
          instance.addLayer({
            id: "asset-points",
            type: "circle",
            source: "assets",
            filter: ["==", ["geometry-type"], "Point"],
            paint: {
              "circle-color": ["case", ["boolean", ["feature-state", "selected"], false], "#059669", "#b45309"],
              "circle-radius": 9,
              "circle-stroke-width": 3,
              "circle-stroke-color": "#ffffff",
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
            if (!asset.geometry) return;
            const assetBounds = new LngLatBounds();
            for (const position of geometryPositions(asset.geometry))
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
            if (asset?.geometry) selectAsset.current?.(asset);
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
  }, [reservoir, assetsJson, records]);
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
          <p className="eyebrow">Geometry</p>
          <div><span className="status-dot" style={{ background: "#059669" }} />Selected</div>
          <div>
            <span className="status-dot" style={{ background: "#b45309" }} />
            Point
          </div>
          <div>
            <span className="legend-line" />
            LineString
          </div>
          <div>
            <span className="legend-polygon" />
            Polygon
          </div>
        </aside>
      </div>
      {assets.length === 0 ? (
        <p className="muted mt-3">
          No assets to map. Centered on the reservoir location.
        </p>
      ) : mapped.length === 0 ? (
        <p className="muted mt-3" role="status">
          Spatial geometry: Not available in this dataset. Asset identities remain
          accessible in the registry. The reservoir center and basemap are
          navigation context, not asset location evidence.
        </p>
      ) : (
        <>
          <p className="muted mt-3 text-sm">
            {mapped.length} of {assets.length} assets have geometry. Geometry
            presence does not imply verification.
            {mapped.length < assets.length &&
              ` ${assets.length - mapped.length} asset(s) without geometry remain in the registry.`}
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

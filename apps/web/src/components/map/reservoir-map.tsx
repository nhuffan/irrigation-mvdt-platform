"use client";
import { documentHref } from "@/lib/document-navigation";
import { observeCanvasResize } from "@/lib/workspace-layout";
import { useEffect, useRef, useState } from "react";
import {
  statusColor,
  statusLabel,
  RESERVOIR_STATUS_LABEL,
} from "@/lib/reservoir-status";
import type { Reservoir } from "@/types/reservoir";

export function ReservoirMap({ reservoirs }: { reservoirs: Reservoir[] }) {
  const container = useRef<HTMLDivElement>(null);
  const reset = useRef<(() => void) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let disposed = false;
    let disposeMap: (() => void) | undefined;
    let stopResize: (() => void) | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    // Import only in the browser: MapLibre 6 uses browser APIs and ESM workers.
    void import("maplibre-gl")
      .then(
        ({
          Map,
          Marker,
          Popup,
          NavigationControl,
          LngLatBounds,
          setWorkerUrl,
        }) => {
          if (disposed || !container.current) return;
          setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
          const map = new Map({
            container: container.current,
            style: "https://demotiles.maplibre.org/style.json",
            center: [0, 20],
            zoom: 1,
          });
          disposeMap = () => map.remove();
          stopResize = observeCanvasResize(container.current, () => map.resize());
          map.addControl(new NavigationControl(), "top-right");
          map.on("load", () => {
            if (!disposed) {
              setLoaded(true);
              setError(null);
            }
            if (timer) clearTimeout(timer);
          });
          map.on("error", () => {
            if (!disposed)
              setError(
                "The basemap could not load completely. Check your connection and reload the page.",
              );
          });
          timer = setTimeout(() => {
            if (!disposed && !map.loaded())
              setError(
                "The basemap is taking longer than expected. Check your connection and reload the page.",
              );
          }, 15000);
          const bounds = new LngLatBounds();
          const markers: InstanceType<typeof Marker>[] = [];
          const popups: InstanceType<typeof Popup>[] = [];
          for (const reservoir of reservoirs) {
            if (
              !Number.isFinite(reservoir.longitude) ||
              !Number.isFinite(reservoir.latitude) ||
              Math.abs(reservoir.longitude) > 180 ||
              Math.abs(reservoir.latitude) > 90
            )
              continue;
            const content = document.createElement("div");
            content.className = "reservoir-popup";
            const title = document.createElement("h3");
            title.textContent = reservoir.name;
            const code = document.createElement("p");
            code.textContent = reservoir.code;
            const status = document.createElement("p");
            status.textContent = `Status: ${statusLabel(reservoir.data_status)}`;
            const level = document.createElement("p");
            level.textContent = `MVDT Level: ${reservoir.mvdt_level}`;
            const link = document.createElement("a");
            link.textContent = "View Reservoir →";
            link.href = documentHref(`/reservoirs/${encodeURIComponent(reservoir.id)}`, window.location.pathname + window.location.search + window.location.hash);
            content.append(title, code, status, level, link);
            const popup = new Popup({
              offset: 20,
              maxWidth: "280px",
            }).setDOMContent(content);
            const button = document.createElement("button");
            button.type = "button";
            button.className = "reservoir-marker";
            button.style.background = statusColor(reservoir.data_status);
            button.setAttribute(
              "aria-label",
              `${reservoir.name} · ${statusLabel(reservoir.data_status)}`,
            );
            button.title = reservoir.name;
            button.setAttribute("aria-expanded", "false");
            popup.on("open", () => {
              popups.forEach((other) => {
                if (other !== popup) other.remove();
              });
              button.setAttribute("aria-expanded", "true");
            });
            popup.on("close", () =>
              button.setAttribute("aria-expanded", "false"),
            );
            const marker = new Marker({ element: button })
              .setLngLat([reservoir.longitude, reservoir.latitude])
              .setPopup(popup)
              .addTo(map);
            markers.push(marker);
            popups.push(popup);
            bounds.extend([reservoir.longitude, reservoir.latitude]);
          }
          reset.current = () => { if (!bounds.isEmpty()) map.fitBounds(bounds, {padding: 70, maxZoom: 9}); };
          if (!bounds.isEmpty())
            map.fitBounds(bounds, { padding: 70, maxZoom: 9, duration: 0 });
          disposeMap = () => {
            markers.forEach((marker) => marker.remove());
            popups.forEach((popup) => popup.remove());
            map.remove();
          };
        },
      )
      .catch(() => {
        if (!disposed)
          setError(
            "The map could not start. Check that WebGL is available in your browser.",
          );
      });
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
      stopResize?.();
      reset.current = null;
      disposeMap?.();
    };
  }, [reservoirs]);
  return (
    <div className="map-frame"><button className="map-reset" disabled={!loaded} onClick={() => reset.current?.()}>Reset map</button>
      <div
        ref={container}
        className="map-canvas"
        aria-label="Reservoir locations map"
      />
      {!loaded && !error && (
        <p className="map-notice" role="status">
          Loading basemap…
        </p>
      )}
      {error && (
        <p className="map-notice" role="alert">
          {error}
        </p>
      )}
      {reservoirs.length === 0 && (
        <p className="map-empty" role="status">
          No reservoirs available.
        </p>
      )}
      <aside className="map-legend" aria-label="Reservoir readiness legend">
        <p className="eyebrow">Data readiness</p>
        {Object.entries(RESERVOIR_STATUS_LABEL).map(([status, label]) => (
          <div key={status}>
            <span
              className="status-dot"
              style={{ background: statusColor(status) }}
            />
            {label}
          </div>
        ))}
      </aside>
    </div>
  );
}

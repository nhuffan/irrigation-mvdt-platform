/** Numeric viewport preferences only: never persist records, documents or evidence. */
export type MapView = { center: [number, number]; zoom: number; bearing: number; pitch: number };
export type CameraView = { position: number[]; direction: number[]; up: number[] };
type ViewStorage = Pick<Storage, "getItem" | "setItem">;
export function viewStorage(): ViewStorage {
  try { return window.sessionStorage; } catch { return { getItem: () => null, setItem: () => {} }; }
}
const finite = (value: unknown, min: number, max: number): value is number => typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;
const vector = (value: unknown): value is number[] => Array.isArray(value) && value.length === 3 && value.every(n => finite(n, -1e9, 1e9));
export function mapView(value: unknown): MapView | null {
  const v = value as MapView | null;
  return v && Array.isArray(v.center) && v.center.length === 2 && finite(v.center[0], -180, 180) && finite(v.center[1], -90, 90) && finite(v.zoom, 0, 24) && finite(v.bearing, -360, 360) && finite(v.pitch, 0, 85)
    ? { center: [v.center[0], v.center[1]], zoom: v.zoom, bearing: v.bearing, pitch: v.pitch } : null;
}
export function cameraView(value: unknown): CameraView | null {
  const v = value as CameraView | null;
  if (!v || !vector(v.position) || !vector(v.direction) || !vector(v.up)) return null;
  const norm = (vector: number[]) => Math.hypot(...vector);
  if (!finite(norm(v.direction), .99, 1.01) || !finite(norm(v.up), .99, 1.01) || Math.abs(v.direction.reduce((sum, n, i) => sum + n * v.up[i], 0)) > .02) return null;
  return { position: [...v.position], direction: [...v.direction], up: [...v.up] };
}
export function readView<T>(storage: ViewStorage, key: string, validate: (value: unknown) => T | null): T | null {
  try {
    const saved = JSON.parse(storage.getItem(`mvdt:view:${key}`) ?? "null");
    return saved?.version === 1 && finite(Date.now() - saved.savedAt, 0, 86400000) ? validate(saved.view) : null;
  } catch { return null; }
}
export function saveView(storage: ViewStorage, key: string, view: MapView | CameraView) {
  try { storage.setItem(`mvdt:view:${key}`, JSON.stringify({ version: 1, savedAt: Date.now(), view })); } catch { /* A blocked/full session store never prevents viewing. */ }
}

/** A request may finish after selection has changed. Never render another scope's payload. */
export function scopedSnapshot<T>(snapshot: { id: string; data: T } | null, id: string): T | null {
  return snapshot?.id === id ? snapshot.data : null;
}

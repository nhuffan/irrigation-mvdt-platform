import type { Asset, AssetLocation } from "../types/asset";
import type { ExplorerData } from "./explorer-data";
export function technicalCoverage(data: ExplorerData) {
  if (data.technical === null) return "Unavailable";
  if (!data.technical.length) return "Missing";
  const levels = [...new Set(data.technical.map(t => t.reviewed_provenance?.verification_level ?? "level unavailable"))];
  return `${data.technical.length} records · ${levels.join(" / ")}`;
}
export function coverageRows(asset: Asset, location: AssetLocation, data: ExplorerData): [string,string][] {
  const events = data.events?.filter(e => e.verification_status === "VERIFIED");
  return [
    ["Identity", asset.data_status === "VERIFIED" ? "Verified identity" : "Available"],
    ["Location", location.location_status === "REFERENCE_LOCATION" ? "Reference" : location.location_status === "VERIFIED_GEOMETRY" ? "Verified" : "Missing"],
    ["Technical", technicalCoverage(data)],
    ["Condition", data.conditionError ? "Unavailable" : data.condition ? "Verified" : "Missing"],
    ...(["INSPECTION", "REPAIR", "MAINTENANCE"] as const).map(type => [type[0]+type.slice(1).toLowerCase(), events === undefined ? "Unavailable" : events.some(e => e.event_type === type) ? `${events.filter(e => e.event_type === type).length} verified` : "Absent — no verified events"] as [string,string]),
    ["Documents", data.documents === null ? "Unavailable" : data.documents.length ? `${data.documents.length} linked file${data.documents.length===1?"":"s"}` : "Absent — no linked files"],
    ["3D", data.links === null ? "Unavailable" : data.links.length ? "Representative mapping" : "Missing"],
  ];
}
export function technicalSources(data: ExplorerData) {
  if (data.technical === null) return "Unavailable";
  if (!data.technical.length) return "No technical claims";
  const ids = new Set(data.technical.flatMap(t => t.source_id ? [t.source_id] : []));
  return `${ids.size} identified source${ids.size === 1 ? "" : "s"}${data.technical.some(t => !t.source_id) ? " · other sources unavailable" : ""}`;
}

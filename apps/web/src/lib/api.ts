import type { TechnicalAttribute } from "@/types/technical-attribute";
import type { Condition } from "@/types/condition";
import type { Inspection } from "@/types/inspection";
import type { Repair } from "@/types/repair";
import type { Maintenance } from "@/types/maintenance";
import type { TimelineEvent } from "@/types/timeline";
import type { Asset } from "@/types/asset";
import type { Reservoir } from "@/types/reservoir";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public status: number) {
    super(`Data API returned ${status}`);
  }
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new ApiError(response.status);
  return response.json();
}

export function getReservoirs(): Promise<Reservoir[]> {
  return request("/reservoirs");
}

export function getReservoir(id: string): Promise<Reservoir> {
  return request(`/reservoirs/${encodeURIComponent(id)}`);
}

export function getReservoirAssets(id: string): Promise<Asset[]> {
  return request(`/reservoirs/${encodeURIComponent(id)}/assets`);
}
export function getAsset(id: string): Promise<Asset> {
  return request(`/assets/${encodeURIComponent(id)}`);
}

export function getAssetTechnical(id: string): Promise<TechnicalAttribute[]> {
  return request(`/assets/${encodeURIComponent(id)}/technical`);
}

export function getAssetConditions(id: string): Promise<Condition[]> {
  return request(`/assets/${encodeURIComponent(id)}/conditions`);
}

export function getAssetInspections(id: string): Promise<Inspection[]> {
  return request(`/assets/${encodeURIComponent(id)}/inspections`);
}

export function getAssetRepairs(id: string): Promise<Repair[]> {
  return request(`/assets/${encodeURIComponent(id)}/repairs`);
}

export function getAssetMaintenance(id: string): Promise<Maintenance[]> {
  return request(`/assets/${encodeURIComponent(id)}/maintenance`);
}

export function getAssetTimeline(id: string): Promise<TimelineEvent[]> {
  return request(`/assets/${encodeURIComponent(id)}/timeline`);
}

export function getAssetCurrentCondition(
  id: string,
): Promise<Condition | null> {
  return request(`/assets/${encodeURIComponent(id)}/current-condition`);
}

export function getAssetDocuments(
  id: string,
): Promise<import("@/types/media").DocumentRecord[]> {
  return request(`/assets/${encodeURIComponent(id)}/documents`);
}
export function getSourceDocuments(
  id: string,
): Promise<import("@/types/media").DocumentRecord[]> {
  return request(`/data-sources/${encodeURIComponent(id)}/documents`);
}
export function getDocument(
  id: string,
): Promise<import("@/types/media").DocumentRecord> {
  return request(`/documents/${encodeURIComponent(id)}`);
}
export function getModels(
  id: string,
): Promise<import("@/types/media").ModelRecord[]> {
  return request(`/reservoirs/${encodeURIComponent(id)}/models`);
}
export function getModelLinks(
  id: string,
): Promise<import("@/types/media").ModelAssetLink[]> {
  return request(`/models/${encodeURIComponent(id)}/asset-links`);
}
export function getAssetModelLinks(
  id: string,
): Promise<import("@/types/media").ModelAssetLink[]> {
  return request(`/assets/${encodeURIComponent(id)}/model-links`);
}

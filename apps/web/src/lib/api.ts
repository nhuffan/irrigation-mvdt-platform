import { MANAGED_RESERVOIR_ID, isManagedReservoir, isResearchAsset, isResearchSource, isResearchModel, visibleDescription } from "./site-scope";
import type { DocumentRecord, ModelRecord } from "../types/media";
import type { DataSource } from "../types/data-source";
import { requestLimit } from "./request-limit";
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

const limitRequest = requestLimit(4);
async function request<T>(path: string): Promise<T> {
 return limitRequest(async () => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new ApiError(response.status);
  return response.json();
 });
}

export async function getReservoirs(): Promise<Reservoir[]> {
  return (await request<Reservoir[]>("/reservoirs")).filter(isManagedReservoir);
}

export async function getReservoir(id: string): Promise<Reservoir> {
  if (id !== MANAGED_RESERVOIR_ID) throw new ApiError(404);
  const record = await request<Reservoir>(`/reservoirs/${encodeURIComponent(id)}`);
  return { ...record, description: visibleDescription(record.description) };
}

export async function getReservoirAssets(id: string): Promise<Asset[]> {
  if (id !== MANAGED_RESERVOIR_ID) throw new ApiError(404);
  return (await request<Asset[]>(`/reservoirs/${encodeURIComponent(id)}/assets`)).filter(isResearchAsset);
}
export async function getAsset(id: string): Promise<Asset> {
  const asset = await request<Asset>(`/assets/${encodeURIComponent(id)}`);
  if (!isResearchAsset(asset)) throw new ApiError(404);
  return { ...asset, description: visibleDescription(asset.description) };
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

export async function getAssetDocuments(
  id: string,
): Promise<import("@/types/media").DocumentRecord[]> {
  return (await request<DocumentRecord[]>(`/assets/${encodeURIComponent(id)}/documents`)).filter(doc => isResearchSource(doc.source));
}
export async function getSourceDocuments(
  id: string,
): Promise<import("@/types/media").DocumentRecord[]> {
  const source = await request<DataSource>(`/data-sources/${encodeURIComponent(id)}`);
  if (!isResearchSource(source)) throw new ApiError(404);
  return (await request<DocumentRecord[]>(`/data-sources/${encodeURIComponent(id)}/documents`)).filter(doc => isResearchSource(doc.source));
}
export async function getDocument(
  id: string,
): Promise<import("@/types/media").DocumentRecord> {
  const doc = await request<DocumentRecord>(`/documents/${encodeURIComponent(id)}`);
  if (!isResearchSource(doc.source)) throw new ApiError(404);
  return doc;
}
export async function getModels(
  id: string,
): Promise<import("@/types/media").ModelRecord[]> {
  if (id !== MANAGED_RESERVOIR_ID) throw new ApiError(404);
  return (await request<ModelRecord[]>(`/reservoirs/${encodeURIComponent(id)}/models`)).filter(isResearchModel);
}
export async function getModelLinks(
  id: string,
): Promise<import("@/types/media").ModelAssetLink[]> {
  await getModel(id);
  const allowed = new Set((await getReservoirAssets(MANAGED_RESERVOIR_ID)).map(a => a.id));
  return (await request<import("../types/media").ModelAssetLink[]>(`/models/${encodeURIComponent(id)}/asset-links`)).filter(link => allowed.has(link.asset_id));
}
export async function getAssetModelLinks(
  id: string,
): Promise<import("@/types/media").ModelAssetLink[]> {
  const allowed = new Set((await getModels(MANAGED_RESERVOIR_ID)).map(m => m.id));
  return (await request<import("../types/media").ModelAssetLink[]>(`/assets/${encodeURIComponent(id)}/model-links`)).filter(link => allowed.has(link.model_id));
}

export async function getModel(id: string): Promise<ModelRecord> {
  const model = await request<ModelRecord>(`/models/${encodeURIComponent(id)}`);
  if (!isResearchModel(model)) throw new ApiError(404);
  return model;
}

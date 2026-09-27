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

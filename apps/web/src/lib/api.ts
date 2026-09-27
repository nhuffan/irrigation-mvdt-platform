import type { Reservoir } from "@/types/reservoir";


const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1";


export async function getReservoirs(): Promise<Reservoir[]> {
  const response = await fetch(
    `${API_BASE_URL}/reservoirs`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Failed to fetch reservoirs: ${response.status}`,
    );
  }

  return response.json();
}

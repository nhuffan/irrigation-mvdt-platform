import { getResearchSummary } from "@/lib/research-summary";
export const dynamic = "force-dynamic";
export async function GET() {
  try {
    return Response.json(await getResearchSummary(), { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ error: "Research summary unavailable. Retry when the data API is reachable." }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}

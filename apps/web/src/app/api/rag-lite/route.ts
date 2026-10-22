import { MANAGED_RESERVOIR_ID } from "@/lib/site-scope";

const base = () => process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const headers = { "Cache-Control": "no-store" };

export async function GET(request: Request) {
  const asset = new URL(request.url).searchParams.get("asset_id");
  if (asset && !/^[0-9a-f-]{36}$/i.test(asset))
    return Response.json({ error: "Invalid asset" }, { status: 400, headers });
  const path = asset
    ? `/demo-questions?asset_id=${encodeURIComponent(asset)}&reservoir_id=${MANAGED_RESERVOIR_ID}`
    : "/status";
  try {
    const response = await fetch(`${base()}/experimental/rag-lite${path}`, {
      cache: "no-store", signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) return Response.json({ error: "Preview unavailable" }, { status: response.status, headers });
    return Response.json(await response.json(), { headers });
  } catch {
    return Response.json({ error: "Preview unavailable" }, { status: 503, headers });
  }
}

export async function POST(request: Request) {
  const origin = request.headers.get("origin");
  if (origin && origin !== new URL(request.url).origin)
    return Response.json({ error: "Invalid origin" }, { status: 403, headers });
  // Stream cap protects against missing/forged Content-Length as well.
  const reader = request.body?.getReader();
  if (!reader) return Response.json({ error: "Missing query" }, { status: 400, headers });
  let body = "";
  let bytes = 0;
  const decoder = new TextDecoder();
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > 8192) {
        await reader.cancel();
        return Response.json({ error: "Query too large" }, { status: 413, headers });
      }
      body += decoder.decode(value, { stream: true });
    }
    body += decoder.decode();
    const payload = JSON.parse(body);
    const response = await fetch(`${base()}/experimental/rag-lite/query`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, reservoir_id: MANAGED_RESERVOIR_ID }),
      cache: "no-store", signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) return Response.json({ error: response.status === 404 ? "Preview disabled" : "Query unavailable or invalid" }, { status: response.status, headers });
    return Response.json(await response.json(), { headers });
  } catch {
    return Response.json({ error: "Query unavailable or invalid" }, { status: 503, headers });
  }
}

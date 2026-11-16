import { MANAGED_RESERVOIR_ID } from "@/lib/site-scope";

const base = () => process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const headers = { "Cache-Control": "no-store" };

function incomingOrigin(request: Request): string | null {
  const url = new URL(request.url);
  const host = request.headers.get("host");
  if (host === null) return url.origin;
  // Next may canonicalize its internal URL hostname. Use the actual Host authority.
  if (!/^(?:[a-z0-9.-]+|\[[a-f0-9:.]+\])(?::\d{1,5})?$/i.test(host)) return null;
  try {
    return new URL(`${url.protocol}//${host}`).origin;
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const asset = params.get("asset_id");
  if (asset && !/^[0-9a-f-]{36}$/i.test(asset))
    return Response.json({ error: "Invalid asset" }, { status: 400, headers });
  const path = params.get("coverage") === "true"
    ? `/coverage?reservoir_id=${MANAGED_RESERVOIR_ID}${asset ? `&asset_id=${encodeURIComponent(asset)}` : ""}`
    : asset
    ? `/demo-questions?asset_id=${encodeURIComponent(asset)}&reservoir_id=${MANAGED_RESERVOIR_ID}`
    : `/status?reservoir_id=${encodeURIComponent(MANAGED_RESERVOIR_ID)}`;
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
  if (origin !== null && origin !== incomingOrigin(request))
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
      cache: "no-store", signal: AbortSignal.any([request.signal, AbortSignal.timeout(15000)]),
    });
    if (!response.ok) return Response.json({ error: response.status === 404 ? "Preview disabled" : "Query unavailable or invalid" }, { status: response.status, headers });
    return Response.json(await response.json(), { headers });
  } catch (error) {
    if (error instanceof Error && error.name === "TimeoutError") {
      return Response.json({ error: "Query timed out" }, { status: 504, headers });
    }
    return Response.json({ error: "Query unavailable or invalid" }, { status: 503, headers });
  }
}

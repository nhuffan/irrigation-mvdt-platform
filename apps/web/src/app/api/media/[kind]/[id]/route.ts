import { ApiError, getDocument, getModel } from "@/lib/api";
import type { NextRequest } from "next/server";
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ kind: string; id: string }> },
) {
  const { kind, id } = await params;
  if (!["documents", "models"].includes(kind) || !/^[0-9a-f-]{36}$/i.test(id))
    return new Response("Not found", { status: 404 });
  const base =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  try {
    if (kind === "documents") await getDocument(id); else await getModel(id);
    const upstream = await fetch(
      `${base}/${kind}/${id}/content?download=${request.nextUrl.searchParams.get("download") === "true"}`,
      {
        cache: "no-store",
        signal: AbortSignal.timeout(30000),
        headers: request.headers.has("range")
          ? { Range: request.headers.get("range")! }
          : {},
      },
    );
    const headers = new Headers({
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      "Content-Security-Policy": "sandbox",
    });
    for (const key of [
      "content-type",
      "content-disposition",
      "content-length",
      "content-range",
      "accept-ranges",
    ]) {
      const value = upstream.headers.get(key);
      if (value) headers.set(key, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers });
  } catch (error) {
    if (error instanceof ApiError && [404, 422].includes(error.status)) return new Response("Not found", { status: 404 });
    return new Response("Unable to load file", { status: 502 });
  }
}

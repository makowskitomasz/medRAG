/**
 * Proxy to the API gateway.
 *
 * This replaces a `rewrites()` entry in next.config.ts. The rewrite proxy buffers
 * the upstream response, so Server-Sent Events from /chat/query/stream only reached
 * the browser once the whole answer was finished — the chat UI sat on "Searching
 * your documents" for the entire query and every pipeline step arrived at once.
 * Returning `upstream.body` directly keeps the stream unbuffered.
 */
const API_GATEWAY = process.env.API_GATEWAY_URL ?? "http://localhost:8000";

// Never cache or pre-render — every call is a live proxy.
export const dynamic = "force-dynamic";

// Hop-by-hop and length headers must not be copied to the proxied response.
const STRIPPED_RESPONSE_HEADERS = new Set([
  "content-encoding",
  "content-length",
  "transfer-encoding",
  "connection",
]);

async function proxy(req: Request, path: string[]): Promise<Response> {
  const url = new URL(req.url);
  const target = `${API_GATEWAY}/${path.join("/")}${url.search}`;

  const headers = new Headers(req.headers);
  // Host must match the upstream, not the Next.js origin.
  headers.delete("host");
  headers.delete("content-length");
  headers.delete("accept-encoding"); // no compression — it would re-buffer the stream

  const hasBody = req.method !== "GET" && req.method !== "HEAD";

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      // Request bodies here are small JSON payloads or file uploads; buffering them
      // is fine and avoids needing a duplex streaming request.
      body: hasBody ? await req.arrayBuffer() : undefined,
      signal: req.signal,
      redirect: "manual",
      cache: "no-store",
    });
  } catch (err) {
    if (req.signal.aborted) return new Response(null, { status: 499 });
    return Response.json(
      { detail: `Gateway unreachable: ${(err as Error).message}` },
      { status: 502 }
    );
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!STRIPPED_RESPONSE_HEADERS.has(key.toLowerCase())) responseHeaders.set(key, value);
  });
  // Tell any proxy in front of Next.js not to buffer either.
  responseHeaders.set("Cache-Control", "no-cache, no-transform");
  responseHeaders.set("X-Accel-Buffering", "no");

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

const handler = async (req: Request, ctx: Ctx) => proxy(req, (await ctx.params).path);

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const HEAD = handler;

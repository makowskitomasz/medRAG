import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

# Hop-by-hop and length headers describe the upstream connection, not the payload.
# Copying them onto a response we re-frame ourselves produces a reply that clients
# (and any proxy in front of us) reject as malformed.
_STRIPPED_HEADERS = frozenset(
    {"content-encoding", "content-length", "transfer-encoding", "connection", "keep-alive"}
)


def _passthrough_headers(headers: httpx.Headers) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() not in _STRIPPED_HEADERS}


async def proxy(request: Request, target_url: str, http: httpx.AsyncClient, user: dict) -> Response:
    headers = dict(request.headers)
    headers["X-User-Id"] = user["user_id"]
    headers["X-User-Role"] = user["role"]
    headers.pop("host", None)

    body = await request.body()

    # Stream on the endpoint's own merits, not just because the caller thought to ask
    # for it. A client sending `Accept: */*` used to fall into the buffered branch and
    # get back a mis-framed response, which surfaced as an opaque gateway error even
    # though the pipeline had run to completion.
    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept or target_url.rstrip("/").endswith("/stream"):
        # Open the upstream connection and check status BEFORE committing to 200 SSE response.
        # This lets validation errors (400/404) propagate properly to the client.
        upstream = http.stream(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
        )
        resp_ctx = await upstream.__aenter__()
        if resp_ctx.status_code >= 400:
            error_body = await resp_ctx.aread()
            await upstream.__aexit__(None, None, None)
            return Response(
                content=error_body,
                status_code=resp_ctx.status_code,
                headers={"Content-Type": "application/json"},
            )

        async def event_stream():
            try:
                async for chunk in resp_ctx.aiter_bytes():
                    yield chunk
            finally:
                await upstream.__aexit__(None, None, None)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    resp = await http.request(
        method=request.method,
        url=target_url,
        headers=headers,
        content=body,
        params=dict(request.query_params),
    )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=_passthrough_headers(resp.headers),
    )

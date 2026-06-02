import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse


async def proxy(request: Request, target_url: str, http: httpx.AsyncClient, user: dict) -> Response:
    headers = dict(request.headers)
    headers["X-User-Id"] = user["user_id"]
    headers["X-User-Role"] = user["role"]
    headers.pop("host", None)

    body = await request.body()

    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept:
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
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

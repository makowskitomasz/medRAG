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

        async def event_stream():
            async with http.stream(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

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

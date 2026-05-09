import httpx
from fastapi import Request, Response


async def proxy(request: Request, target_url: str, http: httpx.AsyncClient, user: dict) -> Response:
    headers = dict(request.headers)
    headers["X-User-Id"] = user["user_id"]
    headers["X-User-Role"] = user["role"]
    headers.pop("host", None)

    body = await request.body()
    resp = await http.request(
        method=request.method,
        url=target_url,
        headers=headers,
        content=body,
        params=dict(request.query_params),
    )
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

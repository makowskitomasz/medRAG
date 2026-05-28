import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

const GATEWAY = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function handler(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const jar = await cookies()
  const token = jar.get("access_token")?.value
  if (!token) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 })

  const { path } = await params
  const targetPath = path.join("/")
  const search = req.nextUrl.search
  const url = `${GATEWAY}/${targetPath}${search}`

  const isStream = req.headers.get("accept") === "text/event-stream"
  const body = req.method !== "GET" && req.method !== "HEAD" ? await req.arrayBuffer() : undefined

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "Content-Type": req.headers.get("content-type") ?? "application/json",
  }
  if (isStream) headers["Accept"] = "text/event-stream"

  const backendRes = await fetch(url, {
    method: req.method,
    headers,
    body: body ?? undefined,
    // @ts-expect-error — Node.js fetch supports duplex
    duplex: "half",
  })

  if (isStream) {
    return new Response(backendRes.body, {
      status: backendRes.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
      },
    })
  }

  const data = await backendRes.arrayBuffer()
  return new Response(data, {
    status: backendRes.status,
    headers: { "Content-Type": backendRes.headers.get("content-type") ?? "application/json" },
  })
}

export const GET = handler
export const POST = handler
export const PATCH = handler
export const DELETE = handler
export const PUT = handler

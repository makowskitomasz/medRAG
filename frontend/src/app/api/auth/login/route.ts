import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

const GATEWAY = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function POST(req: NextRequest) {
  const body = await req.json()

  const backendRes = await fetch(`${GATEWAY}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })

  if (!backendRes.ok) {
    const err = await backendRes.json().catch(() => ({ detail: "Login failed" }))
    return NextResponse.json(err, { status: backendRes.status })
  }

  const data = await backendRes.json()
  const token: string = data.access_token

  const jar = await cookies()
  jar.set("access_token", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24, // 24h
  })

  return NextResponse.json({ ok: true })
}

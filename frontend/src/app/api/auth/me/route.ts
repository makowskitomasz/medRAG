import { cookies } from "next/headers"
import { NextResponse } from "next/server"

const GATEWAY = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function GET() {
  const jar = await cookies()
  const token = jar.get("access_token")?.value
  if (!token) return NextResponse.json({ user: null }, { status: 401 })

  const backendRes = await fetch(`${GATEWAY}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!backendRes.ok) return NextResponse.json({ user: null }, { status: 401 })

  const user = await backendRes.json()
  return NextResponse.json(user)
}

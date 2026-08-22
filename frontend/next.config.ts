import type { NextConfig } from "next";

// NOTE: /api/* is proxied by the route handler in app/api/[...path]/route.ts, not by
// a rewrite — rewrites buffer the response and break SSE streaming.
const nextConfig: NextConfig = {
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
};

export default nextConfig;

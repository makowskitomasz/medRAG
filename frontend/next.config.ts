import type { NextConfig } from "next";

const API_GATEWAY = process.env.API_GATEWAY_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_GATEWAY}/:path*`,
      },
    ];
  },
};

export default nextConfig;

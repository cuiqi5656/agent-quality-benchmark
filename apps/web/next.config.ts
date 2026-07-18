import type { NextConfig } from "next";

const apiBase = process.env.AQB_API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/aqb/:path*", destination: `${apiBase}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          { key: "X-Frame-Options", value: "DENY" }
        ]
      }
    ];
  }
};

export default nextConfig;

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: process.env.NEXT_STATIC_EXPORT === "1" ? "export" : "standalone",
};

export default nextConfig;

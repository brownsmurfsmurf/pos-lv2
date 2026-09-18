import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // BFF 以外の経路を作らない。FastAPI の URL はサーバ側の環境変数 API_UPSTREAM_URL のみが知る（SEC-04）
  poweredByHeader: false,
};

export default nextConfig;

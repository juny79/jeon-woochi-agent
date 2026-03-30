import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // FastAPI 백엔드로 API 요청 프록시 — 브라우저에 백엔드 주소 노출 없음,
  // 프로덕션 배포 시 NEXT_PUBLIC_API_URL 만 바꾸면 됨.
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/backend/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;

import { NextRequest } from "next/server";
import { proxyBackendRequest } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const condition = request.nextUrl.searchParams.get("condition") || "";
  return proxyBackendRequest(
    `/api/v1/analytics/medications?condition=${encodeURIComponent(condition)}`
  );
}

import { NextRequest } from "next/server";
import { proxyBackendRequest } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const timeRange = request.nextUrl.searchParams.get("time_range") || "all";
  return proxyBackendRequest(
    `/api/v1/overview?time_range=${encodeURIComponent(timeRange)}`
  );
}

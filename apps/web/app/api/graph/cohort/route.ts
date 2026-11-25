import { NextRequest } from "next/server";
import { proxyBackendRequest } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const qs = request.nextUrl.searchParams.toString();
  return proxyBackendRequest(`/api/v1/graph/cohort${qs ? `?${qs}` : ""}`);
}

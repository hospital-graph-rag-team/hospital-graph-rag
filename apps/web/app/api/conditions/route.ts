import { proxyBackendRequest } from "@/lib/backend-proxy";

export async function GET() {
  return proxyBackendRequest("/api/v1/conditions");
}

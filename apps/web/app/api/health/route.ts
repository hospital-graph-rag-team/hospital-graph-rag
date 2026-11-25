import { proxyBackendRequest } from "@/lib/backend-proxy";

export async function GET() {
  return proxyBackendRequest("/health", { timeoutMs: 15000, skipDemoGate: true });
}

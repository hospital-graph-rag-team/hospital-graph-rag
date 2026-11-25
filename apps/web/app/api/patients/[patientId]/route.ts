import { NextRequest } from "next/server";
import { proxyBackendRequest } from "@/lib/backend-proxy";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ patientId: string }> }
) {
  const { patientId } = await context.params;
  return proxyBackendRequest(`/api/v1/patients/${encodeURIComponent(patientId)}`);
}

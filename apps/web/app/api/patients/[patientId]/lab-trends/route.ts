import { NextRequest } from "next/server";
import { proxyBackendRequest } from "@/lib/backend-proxy";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ patientId: string }> }
) {
  const { patientId } = await context.params;
  const testName = request.nextUrl.searchParams.get("test_name");
  const qs = testName ? `?test_name=${encodeURIComponent(testName)}` : "";
  return proxyBackendRequest(
    `/api/v1/patients/${encodeURIComponent(patientId)}/lab-trends${qs}`
  );
}

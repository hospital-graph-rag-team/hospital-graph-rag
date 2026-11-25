import { NextRequest, NextResponse } from "next/server";
import { proxyBackendRequest, verifyDemoAccessCookie } from "@/lib/backend-proxy";

export async function POST(request: NextRequest) {
  const authorized = await verifyDemoAccessCookie();
  if (!authorized) {
    return NextResponse.json(
      { detail: "Demo access code required." },
      { status: 401 }
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { detail: "Invalid JSON payload." },
      { status: 400 }
    );
  }
  return proxyBackendRequest("/api/v1/chat", {
    method: "POST",
    body,
    timeoutMs: 50000,
  });
}

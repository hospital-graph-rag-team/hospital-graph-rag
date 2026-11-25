import crypto from "crypto";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const DEMO_COOKIE_NAME = "cg_demo_access";

function resolveBackendBaseUrl(): string {
  const configured = (process.env.BACKEND_URL || "").trim().replace(/\/+$/, "");
  if (configured) {
    return configured;
  }
  if (process.env.NODE_ENV === "production") {
    throw new Error("BACKEND_URL_NOT_CONFIGURED");
  }
  return "http://127.0.0.1:8000";
}

export function isDemoAccessGateEnabled(): boolean {
  return Boolean((process.env.DEMO_ACCESS_CODE || "").trim());
}

export function computeDemoCookieToken(code: string): string {
  return crypto
    .createHash("sha256")
    .update(`clinicalgraph-demo:${code}`)
    .digest("hex");
}

export async function verifyDemoAccessCookie(): Promise<boolean> {
  const requiredCode = (process.env.DEMO_ACCESS_CODE || "").trim();
  if (!requiredCode) {
    return true;
  }
  const cookieStore = await cookies();
  const cookieVal = cookieStore.get(DEMO_COOKIE_NAME)?.value || "";
  const expected = computeDemoCookieToken(requiredCode);
  if (!cookieVal || cookieVal.length !== expected.length) {
    return false;
  }
  return crypto.timingSafeEqual(Buffer.from(cookieVal), Buffer.from(expected));
}

export async function proxyBackendRequest(
  path: string,
  options: {
    method?: "GET" | "POST";
    body?: unknown;
    timeoutMs?: number;
    skipDemoGate?: boolean;
  } = {}
): Promise<NextResponse> {
  if (!options.skipDemoGate) {
    const authorized = await verifyDemoAccessCookie();
    if (!authorized) {
      return NextResponse.json(
        { detail: "Demo access code required." },
        { status: 401 }
      );
    }
  }

  let baseUrl: string;
  try {
    baseUrl = resolveBackendBaseUrl();
  } catch {
    return NextResponse.json(
      { detail: "Frontend server is missing BACKEND_URL configuration." },
      { status: 503 }
    );
  }

  const targetUrl = `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  const backendToken = (process.env.BACKEND_API_TOKEN || "").trim();
  if (backendToken) {
    headers["X-Backend-Token"] = backendToken;
  }
  if (options.method === "POST") {
    headers["Content-Type"] = "application/json";
  }

  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? 25000;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const upstream = await fetch(targetUrl, {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
      signal: controller.signal,
    });

    const text = await upstream.text();
    let payload: unknown;
    try {
      payload = text ? JSON.parse(text) : {};
    } catch {
      payload = { detail: "Backend returned a non-JSON response." };
    }

    return NextResponse.json(payload, { status: upstream.status });
  } catch (err: unknown) {
    const isAbort = err instanceof Error && err.name === "AbortError";
    return NextResponse.json(
      {
        detail: isAbort
          ? "Backend request timed out. If the Render service is waking from cold start, retry in a few seconds."
          : "Unable to reach the ClinicalGraph backend service.",
      },
      { status: isAbort ? 504 : 502 }
    );
  } finally {
    clearTimeout(timer);
  }
}

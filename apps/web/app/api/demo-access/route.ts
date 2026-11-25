import crypto from "crypto";
import { NextRequest, NextResponse } from "next/server";
import {
  computeDemoCookieToken,
  DEMO_COOKIE_NAME,
  isDemoAccessGateEnabled,
  verifyDemoAccessCookie,
} from "@/lib/backend-proxy";

export async function GET() {
  const required = isDemoAccessGateEnabled();
  const unlocked = required ? await verifyDemoAccessCookie() : true;
  return NextResponse.json({ required, unlocked });
}

export async function POST(request: NextRequest) {
  const expectedCode = (process.env.DEMO_ACCESS_CODE || "").trim();
  if (!expectedCode) {
    return NextResponse.json({ unlocked: true });
  }

  let body: { code?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  const submitted = (body.code || "").trim();
  const submittedBuf = Buffer.from(submitted);
  const expectedBuf = Buffer.from(expectedCode);

  if (
    submittedBuf.length !== expectedBuf.length ||
    !crypto.timingSafeEqual(submittedBuf, expectedBuf)
  ) {
    return NextResponse.json({ detail: "Invalid demo access code." }, { status: 401 });
  }

  const isHttps =
    request.nextUrl.protocol === "https:" ||
    request.headers.get("x-forwarded-proto") === "https";

  const res = NextResponse.json({ unlocked: true });
  res.cookies.set(DEMO_COOKIE_NAME, computeDemoCookieToken(expectedCode), {
    httpOnly: true,
    sameSite: "lax",
    secure: isHttps,
    path: "/",
    maxAge: 60 * 60 * 12,
  });
  return res;
}

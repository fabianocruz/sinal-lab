/**
 * Admin content API proxy — forwards authenticated requests to FastAPI.
 *
 * NextAuth uses JWT strategy, so the session token lives in an httpOnly
 * cookie that only the Next.js server can read. This route handler:
 * 1. Verifies the session via auth()
 * 2. Checks the isAdmin flag
 * 3. Forwards the request to FastAPI with X-Admin-Email + X-Admin-Secret
 */

import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ADMIN_SECRET = process.env.ADMIN_API_SECRET || "";

async function proxy(req: NextRequest, { params }: { params: Promise<{ path?: string[] }> }) {
  const session = await auth();

  if (!session?.user?.email) {
    return NextResponse.json({ detail: "Nao autenticado." }, { status: 401 });
  }

  const isAdmin = (session.user as { isAdmin?: boolean }).isAdmin;
  if (!isAdmin) {
    return NextResponse.json({ detail: "Acesso restrito a administradores." }, { status: 403 });
  }

  const { path } = await params;
  const suffix = path?.join("/") ?? "";
  const search = req.nextUrl.search;
  const url = `${API_BASE}/api/admin/content${suffix ? `/${suffix}` : ""}${search}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Admin-Email": session.user.email,
    "X-Admin-Secret": ADMIN_SECRET,
  };

  const body =
    req.method !== "GET" && req.method !== "HEAD"
      ? await req.text().catch(() => undefined)
      : undefined;

  const upstream = await fetch(url, {
    method: req.method,
    headers,
    body: body || undefined,
  });

  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;

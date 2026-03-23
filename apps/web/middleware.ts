/**
 * Next.js middleware — protects /admin/* routes.
 *
 * Uses auth() from NextAuth v5 to read the session directly,
 * ensuring cookie name and secret are consistent with the auth config.
 */

import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

export default auth((req) => {
  const { pathname } = req.nextUrl;

  // Only protect /admin routes — everything else passes through
  if (!pathname.startsWith("/admin")) {
    return NextResponse.next();
  }

  // Not authenticated → login
  if (!req.auth) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Authenticated but not admin → home
  const isAdmin = (req.auth.user as { isAdmin?: boolean })?.isAdmin;
  if (!isAdmin) {
    return NextResponse.redirect(new URL("/", req.url));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/admin/:path*"],
};

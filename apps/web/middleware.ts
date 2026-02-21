/**
 * Next.js middleware — protects /admin/* routes.
 *
 * Checks the NextAuth session for authentication and isAdmin flag.
 * Non-authenticated users are redirected to /login.
 * Authenticated non-admins are redirected to /.
 */

import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

export default auth((req) => {
  const { pathname } = req.nextUrl;

  // Only protect /admin routes
  if (!pathname.startsWith("/admin")) {
    return NextResponse.next();
  }

  const user = req.auth?.user as { isAdmin?: boolean; status?: string } | undefined;

  // Not authenticated → login
  if (!req.auth?.user) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Authenticated but not admin → home
  if (!user?.isAdmin) {
    return NextResponse.redirect(new URL("/", req.url));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/admin/:path*"],
};

import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

export async function GET() {
  const adminEmails = (process.env.ADMIN_EMAILS ?? "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);

  const session = await auth();

  return NextResponse.json({
    ADMIN_EMAILS_raw: process.env.ADMIN_EMAILS,
    ADMIN_EMAILS_parsed: adminEmails,
    AUTH_SECRET_set: !!process.env.AUTH_SECRET,
    session_user_email: session?.user?.email ?? null,
    session_user_isAdmin: (session?.user as { isAdmin?: boolean })?.isAdmin ?? null,
  });
}

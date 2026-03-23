import { NextResponse } from "next/server";

export async function GET() {
  const check = (key: string) => {
    const val = process.env[key];
    if (!val) return "MISSING";
    if (val.includes("\n")) return `HAS_NEWLINE(${val.length})`;
    return `OK(${val.length})`;
  };

  return NextResponse.json({
    GOOGLE_CLIENT_ID: check("GOOGLE_CLIENT_ID"),
    GOOGLE_CLIENT_SECRET: check("GOOGLE_CLIENT_SECRET"),
    AUTH_GOOGLE_ID: check("AUTH_GOOGLE_ID"),
    AUTH_GOOGLE_SECRET: check("AUTH_GOOGLE_SECRET"),
    AUTH_SECRET: check("AUTH_SECRET"),
    NEXTAUTH_SECRET: check("NEXTAUTH_SECRET"),
    NEXTAUTH_URL: check("NEXTAUTH_URL"),
    NEXT_PUBLIC_API_URL: check("NEXT_PUBLIC_API_URL"),
    NEXT_PUBLIC_SITE_URL: check("NEXT_PUBLIC_SITE_URL"),
  });
}

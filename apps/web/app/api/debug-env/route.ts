import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID ? "SET" : "MISSING",
    GOOGLE_CLIENT_SECRET: process.env.GOOGLE_CLIENT_SECRET ? "SET" : "MISSING",
    AUTH_GOOGLE_ID: process.env.AUTH_GOOGLE_ID ? "SET" : "MISSING",
    AUTH_GOOGLE_SECRET: process.env.AUTH_GOOGLE_SECRET ? "SET" : "MISSING",
    AUTH_SECRET: process.env.AUTH_SECRET ? "SET" : "MISSING",
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET ? "SET" : "MISSING",
    NEXTAUTH_URL: process.env.NEXTAUTH_URL ?? "MISSING",
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "MISSING",
  });
}

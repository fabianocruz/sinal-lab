import { NextResponse } from "next/server";

export async function GET() {
  const gid = process.env.AUTH_GOOGLE_ID ?? "";
  const gsecret = process.env.AUTH_GOOGLE_SECRET ?? "";

  // Test OIDC discovery fetch
  let discoveryOk = false;
  let discoveryError = "";
  try {
    const res = await fetch(
      "https://accounts.google.com/.well-known/openid-configuration"
    );
    discoveryOk = res.ok;
  } catch (e) {
    discoveryError = String(e);
  }

  return NextResponse.json({
    clientId_length: gid.length,
    clientId_prefix: gid.substring(0, 10),
    clientSecret_length: gsecret.length,
    clientSecret_prefix: gsecret.substring(0, 8),
    clientId_has_whitespace: gid !== gid.trim(),
    clientSecret_has_whitespace: gsecret !== gsecret.trim(),
    discoveryOk,
    discoveryError: discoveryError || undefined,
  });
}

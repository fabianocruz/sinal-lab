/**
 * NextAuth v5 configuration.
 *
 * Providers:
 *   - CredentialsProvider: calls POST /api/auth/verify on the FastAPI backend
 *   - GoogleProvider: OAuth via GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
 *
 * Session strategy: JWT (stateless — no NextAuth database adapter needed).
 * The FastAPI backend owns the user database.
 */

import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";
import { cookies } from "next/headers";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UTMPayload {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  referrer?: string;
  landing_path?: string;
}

/**
 * Read `sinal_utm` cookie (set by <UTMCapture /> on first visit) and
 * parse its JSON payload. Returns null when the cookie is missing or
 * malformed. This is the server-side counterpart to `readUTMWithContext`
 * (which uses localStorage in the browser).
 */
async function readUTMCookie(): Promise<UTMPayload | null> {
  try {
    const store = await cookies();
    const raw = store.get("sinal_utm")?.value;
    if (!raw) return null;
    const parsed = JSON.parse(decodeURIComponent(raw));
    if (typeof parsed !== "object" || parsed === null) return null;
    const utm: UTMPayload = {};
    if (parsed.utm_source) utm.utm_source = String(parsed.utm_source).slice(0, 100);
    if (parsed.utm_medium) utm.utm_medium = String(parsed.utm_medium).slice(0, 100);
    if (parsed.utm_campaign) utm.utm_campaign = String(parsed.utm_campaign).slice(0, 200);
    if (parsed.referrer) utm.referrer = String(parsed.referrer).slice(0, 500);
    if (parsed.landing_path) utm.landing_path = String(parsed.landing_path).slice(0, 500);
    return Object.keys(utm).length ? utm : null;
  } catch {
    return null;
  }
}

/**
 * Fetch with a single retry — handles Railway cold-start 502s.
 * Waits 2s before the retry to give the backend time to wake up.
 */
async function fetchWithRetry(url: string, init: globalThis.RequestInit): Promise<Response> {
  const res = await fetch(url, init);
  if (res.status === 502) {
    await new Promise((r) => setTimeout(r, 2000));
    return fetch(url, init);
  }
  return res;
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Senha", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          const response = await fetchWithRetry(`${API_BASE}/api/auth/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });

          if (!response.ok) {
            return null;
          }

          const user = await response.json();

          return {
            id: String(user.id),
            email: user.email,
            name: user.name ?? null,
            image: user.avatar_url ?? null,
            status: user.status,
          };
        } catch {
          return null;
        }
      },
    }),

    GoogleProvider({
      clientId: process.env.AUTH_GOOGLE_ID,
      clientSecret: process.env.AUTH_GOOGLE_SECRET,
    }),
  ],

  pages: {
    signIn: "/login",
    newUser: "/cadastro",
  },

  session: {
    strategy: "jwt",
  },

  callbacks: {
    async signIn({ user, account }) {
      // Sync Google OAuth users to FastAPI backend (PostgreSQL).
      // Creates the user if new, upgrades waitlist users, and triggers
      // welcome email. Graceful degradation: if backend is down, sign-in
      // still succeeds (user exists only in JWT until next sync).
      if (account?.provider === "google" && user.email) {
        try {
          // Bridge client-side UTM (localStorage via <UTMCapture />) to this
          // server-side callback via the sinal_utm cookie. Cookie is set on
          // first visit, so even a user who lands 2 weeks ago and signs up
          // today still carries first-touch attribution.
          const utm = await readUTMCookie();
          const res = await fetchWithRetry(`${API_BASE}/api/auth/sync-oauth`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: user.email,
              name: user.name ?? undefined,
              avatar_url: user.image ?? undefined,
              provider: "google",
              provider_id: account.providerAccountId,
              utm: utm ?? undefined,
            }),
          });
          if (!res.ok) {
            console.error(
              `[auth] sync-oauth failed for ${user.email}: ${res.status} ${res.statusText}`,
            );
          }
        } catch (err) {
          console.error(`[auth] sync-oauth unreachable for ${user.email}:`, err);
        }
      }
      return true;
    },

    async jwt({ token, user }) {
      // On first sign-in, `user` is populated — persist fields into the token.
      if (user) {
        token.id = user.id;
        // `status` is a custom field added by CredentialsProvider.authorize.
        // For Google sign-ins it will be undefined; default to "active".
        token.status = (user as { status?: string }).status ?? "active";
      }
      // Check admin status via email allowlist (ADMIN_EMAILS env var)
      const adminEmails = (process.env.ADMIN_EMAILS ?? "")
        .split(",")
        .map((e) => e.trim().toLowerCase())
        .filter(Boolean);
      token.isAdmin = adminEmails.includes((token.email ?? "").toLowerCase());
      return token;
    },

    async session({ session, token }) {
      // Expose id, status, and isAdmin on the client-side session object.
      if (session.user) {
        session.user.id = token.id as string;
        (session.user as { status?: string }).status = token.status as string;
        (session.user as { isAdmin?: boolean }).isAdmin = (token.isAdmin as boolean) ?? false;
      }
      return session;
    },
  },
});

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
          const response = await fetch(`${API_BASE}/api/auth/verify`, {
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
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
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
          await fetch(`${API_BASE}/api/auth/sync-oauth`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: user.email,
              name: user.name ?? undefined,
              avatar_url: user.image ?? undefined,
              provider: "google",
              provider_id: account.providerAccountId,
            }),
          });
        } catch {
          // Backend unreachable — allow sign-in anyway
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

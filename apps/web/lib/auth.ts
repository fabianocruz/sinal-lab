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
    async jwt({ token, user }) {
      // On first sign-in, `user` is populated — persist fields into the token.
      if (user) {
        token.id = user.id;
        // `status` is a custom field added by CredentialsProvider.authorize.
        // For Google sign-ins it will be undefined; default to "active".
        token.status = (user as { status?: string }).status ?? "active";
      }
      return token;
    },

    async session({ session, token }) {
      // Expose id and status on the client-side session object.
      if (session.user) {
        session.user.id = token.id as string;
        (session.user as { status?: string }).status = token.status as string;
      }
      return session;
    },
  },
});

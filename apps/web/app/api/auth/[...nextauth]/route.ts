/**
 * NextAuth API route handler.
 *
 * Catches all requests to /api/auth/* (GET and POST) and delegates them
 * to the NextAuth handlers configured in lib/auth.ts.
 */

import { handlers } from "@/lib/auth";

export const { GET, POST } = handlers;

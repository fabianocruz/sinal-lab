"use client";

import { useSearchParams } from "next/navigation";
import { useEffect } from "react";

/**
 * Reads UTM parameters from the URL and stores them in localStorage so they
 * can be attached to the signup request later. Renders nothing.
 *
 * Must be rendered inside a Suspense boundary because useSearchParams()
 * suspends during SSR hydration.
 */
export function UTMCapture() {
  const searchParams = useSearchParams();

  useEffect(() => {
    const utm = {
      utm_source: searchParams.get("utm_source") || "",
      utm_medium: searchParams.get("utm_medium") || "",
      utm_campaign: searchParams.get("utm_campaign") || "",
    };

    // Only persist if at least one UTM value is present.
    if (utm.utm_source || utm.utm_medium || utm.utm_campaign) {
      const serialized = JSON.stringify(utm);
      try {
        localStorage.setItem("sinal_utm", serialized);
      } catch {
        // localStorage may be blocked (private browsing, etc.) — ignore silently.
      }
      // Mirror to a cookie so the NextAuth server-side callback can read
      // attribution for Google OAuth signups (localStorage is browser-only).
      // 30-day expiry, SameSite=Lax, not httpOnly (no secrets inside).
      try {
        const maxAge = 60 * 60 * 24 * 30; // 30 days
        const secure = window.location.protocol === "https:" ? "; Secure" : "";
        document.cookie = `sinal_utm=${encodeURIComponent(serialized)}; Max-Age=${maxAge}; Path=/; SameSite=Lax${secure}`;
      } catch {
        // Cookies may be blocked — ignore silently.
      }
    }
  }, [searchParams]);

  return null;
}

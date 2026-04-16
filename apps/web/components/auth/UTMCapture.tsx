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
      try {
        localStorage.setItem("sinal_utm", JSON.stringify(utm));
      } catch {
        // localStorage may be blocked (private browsing, etc.) — ignore silently.
      }
    }
  }, [searchParams]);

  return null;
}

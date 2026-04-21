/**
 * UTM attribution helpers.
 *
 * UTMs are captured on first visit by <UTMCapture /> and persisted in
 * localStorage (key: "sinal_utm"). These helpers read that payload so
 * signup/waitlist requests can forward the data to the backend.
 */

export interface SinalUTM {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  referrer?: string;
  landing_path?: string;
}

const STORAGE_KEY = "sinal_utm";

/**
 * Read stored UTM data from localStorage. Returns `null` when nothing is
 * stored, localStorage is unavailable (private browsing), or the value
 * cannot be parsed as JSON.
 */
export function readStoredUTM(): SinalUTM | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return null;
    const utm: SinalUTM = {};
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
 * Same as readStoredUTM() but also pulls referrer and landing path from
 * the current document so the backend gets full attribution context even
 * when the original visit was on another page.
 */
export function readUTMWithContext(): SinalUTM | null {
  const stored = readStoredUTM() ?? {};
  if (typeof window !== "undefined") {
    if (!stored.referrer && document.referrer) {
      stored.referrer = document.referrer.slice(0, 500);
    }
    if (!stored.landing_path && window.location?.pathname) {
      stored.landing_path = window.location.pathname.slice(0, 500);
    }
  }
  return Object.keys(stored).length ? stored : null;
}

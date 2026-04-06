/**
 * API Client for FastAPI Backend.
 *
 * Ported from Vite SPA. Uses NEXT_PUBLIC_API_URL instead of VITE_API_BASE_URL.
 */

import type { Company } from "@/lib/company";
import type { ContentApiItem } from "@/lib/newsletter";
import type {
  Signal,
  SignalCluster,
  WeeklyPulse,
  SignalStats,
  Voice,
  SignalEntity,
  CuratedFeedItem,
} from "@/lib/signal";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WaitlistSignupData {
  email: string;
  name?: string;
  company?: string;
  role?: string;
  plan?: string;
}

export interface WaitlistSignupResponse {
  message: string;
  email: string;
  position?: number;
}

export interface AgentSummary {
  agent_name: string;
  last_run: string | null;
  status: "active" | "idle" | "error";
  items_processed: number;
  avg_confidence: number;
  sources: number;
  error_count: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

export async function submitWaitlist(data: WaitlistSignupData): Promise<WaitlistSignupResponse> {
  const response = await fetch(`${API_BASE}/api/waitlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to submit to waitlist" }));
    throw new Error(error.detail || "Failed to submit to waitlist");
  }

  return response.json();
}

export async function fetchWaitlistCount(): Promise<number> {
  try {
    const response = await fetch(`${API_BASE}/api/waitlist/count`);
    if (!response.ok) return 247;
    const data = await response.json();
    return data.count || 247;
  } catch {
    return 247;
  }
}

export async function fetchAgentSummaries(): Promise<AgentSummary[]> {
  try {
    const response = await fetch(`${API_BASE}/api/agents/summary`);
    if (!response.ok) return [];
    return response.json();
  } catch {
    return [];
  }
}

export async function fetchLatestNewsletter(): Promise<ContentApiItem | null> {
  try {
    const response = await fetch(`${API_BASE}/api/content/newsletter/latest`, {
      next: { revalidate: 60 },
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function fetchFeaturedContent(): Promise<ContentApiItem | null> {
  try {
    const url = `${API_BASE}/api/content?status=published&agent_name=radar&limit=1`;
    const response = await fetch(url, { next: { revalidate: 60 } });
    if (!response.ok) return null;
    const data: PaginatedResponse<ContentApiItem> = await response.json();
    return data.items?.[0] ?? null;
  } catch {
    return null;
  }
}

export async function fetchNewsletters(params?: {
  agent_name?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<ContentApiItem>> {
  try {
    const searchParams = new URLSearchParams();
    searchParams.set("status", "published");
    searchParams.set("content_type_exclude", "ARTICLE,INTELLIGENCE");
    if (params?.agent_name) searchParams.set("agent_name", params.agent_name);
    if (params?.search) searchParams.set("search", params.search);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));

    const url = `${API_BASE}/api/content?${searchParams.toString()}`;
    const response = await fetch(url, { next: { revalidate: 60 } });
    if (!response.ok) return { items: [], total: 0, limit: 20, offset: 0 };
    return response.json();
  } catch {
    return { items: [], total: 0, limit: 20, offset: 0 };
  }
}

export async function fetchArticles(params?: {
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<ContentApiItem>> {
  try {
    const searchParams = new URLSearchParams();
    searchParams.set("status", "published");
    searchParams.set("content_type", "ARTICLE");
    if (params?.search) searchParams.set("search", params.search);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));

    const url = `${API_BASE}/api/content?${searchParams.toString()}`;
    const response = await fetch(url, { next: { revalidate: 60 } });
    if (!response.ok) return { items: [], total: 0, limit: 20, offset: 0 };
    return response.json();
  } catch {
    return { items: [], total: 0, limit: 20, offset: 0 };
  }
}

export async function fetchNewsletterBySlug(slug: string): Promise<ContentApiItem | null> {
  try {
    const response = await fetch(`${API_BASE}/api/content/${slug}`, {
      next: { revalidate: 300 },
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Companies
// ---------------------------------------------------------------------------

export async function fetchCompanies(params?: {
  sector?: string;
  city?: string;
  country?: string;
  tags?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<Company>> {
  try {
    const searchParams = new URLSearchParams();
    if (params?.sector) searchParams.set("sector", params.sector);
    if (params?.city) searchParams.set("city", params.city);
    if (params?.country) searchParams.set("country", params.country);
    if (params?.tags) searchParams.set("tags", params.tags);
    if (params?.search) searchParams.set("search", params.search);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));

    const url = `${API_BASE}/api/companies?${searchParams.toString()}`;
    const response = await fetch(url, { next: { revalidate: 60 } });
    if (!response.ok) return { items: [], total: 0, limit: 20, offset: 0 };
    return response.json();
  } catch {
    return { items: [], total: 0, limit: 20, offset: 0 };
  }
}

export interface CompanyStats {
  total: number;
  countries: number;
  sectors: number;
}

export async function fetchCompanyStats(): Promise<CompanyStats> {
  try {
    const response = await fetch(`${API_BASE}/api/companies/stats`, {
      next: { revalidate: 60 },
    });
    if (!response.ok) return { total: 0, countries: 0, sectors: 0 };
    return response.json();
  } catch {
    return { total: 0, countries: 0, sectors: 0 };
  }
}

export async function fetchCompanyBySlug(slug: string): Promise<Company | null> {
  try {
    const encoded = encodeURIComponent(slug);
    const response = await fetch(`${API_BASE}/api/companies/${encoded}`, {
      next: { revalidate: 300 },
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Developers — API Access Request
// ---------------------------------------------------------------------------

export interface ApiAccessRequestData {
  name: string;
  email: string;
  company: string;
  role: string;
  use_case: string;
}

export async function submitApiAccessRequest(
  data: ApiAccessRequestData,
): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/api/developers/request-access`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Erro ao enviar solicitação." }));
    throw new Error(error.detail || "Erro ao enviar solicitação.");
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Intelligence Reports
// ---------------------------------------------------------------------------

export async function fetchIntelligenceReports(params?: {
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<ContentApiItem>> {
  try {
    const searchParams = new URLSearchParams();
    searchParams.set("status", "published");
    searchParams.set("content_type", "INTELLIGENCE");
    if (params?.search) searchParams.set("search", params.search);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));

    const url = `${API_BASE}/api/content?${searchParams.toString()}`;
    const response = await fetch(url, { next: { revalidate: 60 } });
    if (!response.ok) return { items: [], total: 0, limit: 20, offset: 0 };
    return response.json();
  } catch {
    return { items: [], total: 0, limit: 20, offset: 0 };
  }
}

export async function fetchLatestIntelligence(): Promise<ContentApiItem | null> {
  try {
    const data = await fetchIntelligenceReports({ limit: 1 });
    return data.items?.[0] ?? null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Signals
// ---------------------------------------------------------------------------

export async function fetchSignalStats(): Promise<SignalStats> {
  try {
    const response = await fetch(`${API_BASE}/api/signals/stats`, {
      next: { revalidate: 300 },
    });
    if (!response.ok)
      return { total_signals: 0, total_clusters: 0, total_voices: 0, platforms: {}, themes: {} };
    return response.json();
  } catch {
    return { total_signals: 0, total_clusters: 0, total_voices: 0, platforms: {}, themes: {} };
  }
}

export async function fetchSignalClusters(params?: {
  theme?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<SignalCluster>> {
  try {
    const searchParams = new URLSearchParams();
    if (params?.theme) searchParams.set("theme", params.theme);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));

    const qs = searchParams.toString();
    const url = `${API_BASE}/api/signals/clusters${qs ? `?${qs}` : ""}`;
    const response = await fetch(url, { next: { revalidate: 300 } });
    if (!response.ok) return { items: [], total: 0, limit: 20, offset: 0 };
    return response.json();
  } catch {
    return { items: [], total: 0, limit: 20, offset: 0 };
  }
}

export async function fetchSignalClusterBySlug(slug: string): Promise<SignalCluster | null> {
  try {
    const encoded = encodeURIComponent(slug);
    const response = await fetch(`${API_BASE}/api/signals/clusters/${encoded}`, {
      next: { revalidate: 300 },
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function fetchLatestPulse(): Promise<WeeklyPulse | null> {
  try {
    const response = await fetch(`${API_BASE}/api/signals/pulse`, {
      next: { revalidate: 300 },
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function fetchSignals(params?: {
  platform?: string;
  theme?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<Signal>> {
  try {
    const searchParams = new URLSearchParams();
    if (params?.platform) searchParams.set("platform", params.platform);
    if (params?.theme) searchParams.set("theme", params.theme);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));

    const qs = searchParams.toString();
    const url = `${API_BASE}/api/signals${qs ? `?${qs}` : ""}`;
    const response = await fetch(url, { next: { revalidate: 300 } });
    if (!response.ok) return { items: [], total: 0, limit: 20, offset: 0 };
    return response.json();
  } catch {
    return { items: [], total: 0, limit: 20, offset: 0 };
  }
}

/**
 * Fetches curated feed items from the Feed Curator Agent endpoint.
 *
 * Falls back to raw signals re-shaped as CuratedFeedItems when the curated
 * endpoint is unavailable (404, network error, or empty result).
 *
 * Returns { items, total, limit, offset, isCurated } where isCurated
 * indicates whether the response came from the real curated endpoint.
 */
export async function fetchCuratedFeed(params?: {
  limit?: number;
  offset?: number;
  theme?: string;
}): Promise<PaginatedResponse<CuratedFeedItem> & { isCurated: boolean }> {
  const searchParams = new URLSearchParams();
  if (params?.theme) searchParams.set("theme", params.theme);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();

  try {
    const url = `${API_BASE}/api/signals/feed${qs ? `?${qs}` : ""}`;
    const response = await fetch(url, { next: { revalidate: 60 } });
    if (response.ok) {
      const data: PaginatedResponse<CuratedFeedItem> = await response.json();
      if (data.items.length > 0) {
        return { ...data, isCurated: true };
      }
    }
  } catch {
    // Fall through to raw-signal fallback
  }

  // Fallback: fetch raw signals and re-shape them into CuratedFeedItems
  const raw = await fetchSignals(params);
  const items: CuratedFeedItem[] = raw.items.map((s) => ({
    id: s.id,
    editorial_headline: s.text.slice(0, 120).trimEnd() + (s.text.length > 120 ? "..." : ""),
    editorial_context: null,
    original_text: s.text,
    original_url: s.post_url,
    platform: s.platform,
    author_handle: s.author_handle,
    author_display_name: s.author_display_name,
    thumbnail_url: null,
    video_embed: null,
    theme: s.theme,
    category: s.sub_theme || s.theme,
    relevance_score: s.authority_score,
    metrics: s.metrics as Record<string, number> | null,
    curated_at: s.published_at,
  }));

  return { items, total: raw.total, limit: raw.limit, offset: raw.offset, isCurated: false };
}

export async function fetchVoices(params?: {
  account_type?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<Voice>> {
  try {
    const searchParams = new URLSearchParams();
    if (params?.account_type) searchParams.set("account_type", params.account_type);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));

    const qs = searchParams.toString();
    const url = `${API_BASE}/api/signals/voices${qs ? `?${qs}` : ""}`;
    const response = await fetch(url, { next: { revalidate: 300 } });
    if (!response.ok) return { items: [], total: 0, limit: 20, offset: 0 };
    return response.json();
  } catch {
    return { items: [], total: 0, limit: 20, offset: 0 };
  }
}

export async function fetchSignalEntities(params?: {
  theme?: string;
  limit?: number;
}): Promise<PaginatedResponse<SignalEntity>> {
  try {
    const searchParams = new URLSearchParams();
    if (params?.theme) searchParams.set("theme", params.theme);
    if (params?.limit) searchParams.set("limit", String(params.limit));

    const qs = searchParams.toString();
    const url = `${API_BASE}/api/signals/entities${qs ? `?${qs}` : ""}`;
    const response = await fetch(url, { next: { revalidate: 300 } });
    if (!response.ok) return { items: [], total: 0, limit: 20, offset: 0 };
    return response.json();
  } catch {
    return { items: [], total: 0, limit: 20, offset: 0 };
  }
}

// ---------------------------------------------------------------------------
// Watchlist
// ---------------------------------------------------------------------------

export interface WatchlistItem {
  id: string;
  user_email: string;
  item_type: string;
  item_slug: string;
  item_name: string;
  created_at: string | null;
}

export async function fetchWatchlist(email: string): Promise<WatchlistItem[]> {
  try {
    const encoded = encodeURIComponent(email);
    const response = await fetch(`${API_BASE}/api/signals/watchlist?email=${encoded}`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.items ?? [];
  } catch {
    return [];
  }
}

export async function addToWatchlist(
  email: string,
  itemType: string,
  slug: string,
  name: string,
): Promise<WatchlistItem | null> {
  try {
    const response = await fetch(`${API_BASE}/api/signals/watchlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        item_type: itemType,
        item_slug: slug,
        item_name: name,
      }),
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function removeFromWatchlist(itemId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/signals/watchlist/${itemId}`, {
      method: "DELETE",
    });
    return response.status === 204;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

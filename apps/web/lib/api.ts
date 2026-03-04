/**
 * API Client for FastAPI Backend.
 *
 * Ported from Vite SPA. Uses NEXT_PUBLIC_API_URL instead of VITE_API_BASE_URL.
 */

import type { Company } from "@/lib/company";
import type { ContentApiItem } from "@/lib/newsletter";

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
    searchParams.set("content_type_exclude", "ARTICLE");
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

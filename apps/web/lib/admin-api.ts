/**
 * Admin API client — CRUD operations for content management.
 *
 * All functions send the session token via Authorization header.
 * Used by /admin/* pages to interact with the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AdminContent {
  id: string;
  title: string;
  slug: string;
  subtitle: string | null;
  body_md: string;
  content_type: string;
  agent_name: string | null;
  review_status: string;
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  sources: string[] | null;
  confidence_dq: number | null;
  meta_description: string | null;
}

export interface AdminContentList {
  items: AdminContent[];
  total: number;
  limit: number;
  offset: number;
}

export interface ContentCreateData {
  title: string;
  subtitle?: string;
  body_md: string;
  content_type: string;
  summary?: string;
  meta_description?: string;
  sources?: string[];
}

export interface ContentUpdateData {
  title?: string;
  subtitle?: string;
  body_md?: string;
  content_type?: string;
  summary?: string;
  meta_description?: string;
  sources?: string[];
}

async function adminFetch<T>(path: string, options: globalThis.RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}/api/admin/content${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Admin API error: ${res.status} ${res.statusText}`);
  }

  // 204 No Content (delete)
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export async function adminListContent(params?: {
  content_type?: string;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<AdminContentList> {
  const searchParams = new URLSearchParams();
  if (params?.content_type) searchParams.set("content_type", params.content_type);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));

  const qs = searchParams.toString();
  return adminFetch<AdminContentList>(qs ? `?${qs}` : "");
}

export async function adminGetContent(slug: string): Promise<AdminContent> {
  return adminFetch<AdminContent>(`/${slug}`);
}

export async function adminCreateContent(data: ContentCreateData): Promise<AdminContent> {
  return adminFetch<AdminContent>("", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminUpdateContent(
  slug: string,
  data: ContentUpdateData,
): Promise<AdminContent> {
  return adminFetch<AdminContent>(`/${slug}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteContent(slug: string): Promise<void> {
  return adminFetch<void>(`/${slug}`, { method: "DELETE" });
}

export async function adminPublishContent(slug: string): Promise<AdminContent> {
  return adminFetch<AdminContent>(`/${slug}/publish`, { method: "POST" });
}

export async function adminUnpublishContent(slug: string): Promise<AdminContent> {
  return adminFetch<AdminContent>(`/${slug}/unpublish`, { method: "POST" });
}

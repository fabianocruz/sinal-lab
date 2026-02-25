import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  submitWaitlist,
  fetchWaitlistCount,
  fetchAgentSummaries,
  fetchLatestNewsletter,
  fetchNewsletters,
  fetchNewsletterBySlug,
  healthCheck,
  type WaitlistSignupData,
  type WaitlistSignupResponse,
  type AgentSummary,
  type NewsletterItem,
  type PaginatedResponse,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Creates a minimal mock Response object compatible with the fetch API. */
function mockResponse<T>(body: T, options: { ok?: boolean; status?: number } = {}): Response {
  const { ok = true, status = 200 } = options;
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response;
}

/** Creates a mock Response that simulates a non-2xx failure. */
function mockErrorResponse(status = 500, body: unknown = { detail: "Server error" }): Response {
  return mockResponse(body, { ok: false, status });
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// submitWaitlist
// ---------------------------------------------------------------------------

describe("submitWaitlist", () => {
  const payload: WaitlistSignupData = {
    email: "test@example.com",
    name: "Test User",
    company: "Acme",
    role: "CTO",
  };

  const successBody: WaitlistSignupResponse = {
    message: "Signed up",
    email: "test@example.com",
    position: 42,
  };

  it("sends POST to /api/waitlist with JSON body and Content-Type header", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(successBody));

    await submitWaitlist(payload);

    expect(fetch).toHaveBeenCalledOnce();
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("/api/waitlist");
    expect(init?.method).toBe("POST");
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(init?.body).toBe(JSON.stringify(payload));
  });

  it("returns the parsed response on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(successBody));

    const result = await submitWaitlist(payload);

    expect(result).toEqual(successBody);
  });

  it("sends only email when optional fields are omitted", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(successBody));

    const minimalPayload: WaitlistSignupData = { email: "minimal@example.com" };
    await submitWaitlist(minimalPayload);

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.body).toBe(JSON.stringify(minimalPayload));
  });

  it("throws with error detail message when response is not ok", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockErrorResponse(400, { detail: "Email already registered" }),
    );

    await expect(submitWaitlist(payload)).rejects.toThrow("Email already registered");
  });

  it("throws generic message when error response has no detail field", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(500, {}));

    await expect(submitWaitlist(payload)).rejects.toThrow("Failed to submit to waitlist");
  });

  it("throws generic message when error response body is not valid JSON", async () => {
    const badResponse: Response = {
      ok: false,
      status: 500,
      json: vi.fn().mockRejectedValue(new SyntaxError("Unexpected token")),
    } as unknown as Response;
    vi.mocked(fetch).mockResolvedValue(badResponse);

    await expect(submitWaitlist(payload)).rejects.toThrow("Failed to submit to waitlist");
  });

  it("propagates network errors (fetch throws)", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("Network failure"));

    await expect(submitWaitlist(payload)).rejects.toThrow("Network failure");
  });

  it("includes plan field when provided", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(successBody));

    const payloadWithPlan: WaitlistSignupData = { email: "test@example.com", plan: "pro" };
    await submitWaitlist(payloadWithPlan);

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(JSON.parse(init?.body as string)).toEqual(
      expect.objectContaining({ email: "test@example.com", plan: "pro" }),
    );
  });
});

// ---------------------------------------------------------------------------
// fetchWaitlistCount
// ---------------------------------------------------------------------------

describe("fetchWaitlistCount", () => {
  it("returns the count from the API on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ count: 512 }));

    const result = await fetchWaitlistCount();

    expect(result).toBe(512);
  });

  it("returns fallback 247 when response is not ok", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(503));

    const result = await fetchWaitlistCount();

    expect(result).toBe(247);
  });

  it("returns fallback 247 when fetch throws a network error", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("DNS lookup failed"));

    const result = await fetchWaitlistCount();

    expect(result).toBe(247);
  });

  it("returns fallback 247 when response body has no count field", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({}));

    const result = await fetchWaitlistCount();

    expect(result).toBe(247);
  });

  it("calls the correct endpoint /api/waitlist/count", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ count: 1 }));

    await fetchWaitlistCount();

    expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/api/waitlist/count");
  });
});

// ---------------------------------------------------------------------------
// fetchAgentSummaries
// ---------------------------------------------------------------------------

describe("fetchAgentSummaries", () => {
  const mockSummaries: AgentSummary[] = [
    {
      agent_name: "sintese",
      last_run: "2026-02-10T10:00:00Z",
      status: "active",
      items_processed: 100,
      avg_confidence: 0.85,
      sources: 5,
      error_count: 0,
    },
    {
      agent_name: "radar",
      last_run: null,
      status: "idle",
      items_processed: 0,
      avg_confidence: 0,
      sources: 0,
      error_count: 0,
    },
  ];

  it("returns the parsed array on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockSummaries));

    const result = await fetchAgentSummaries();

    expect(result).toEqual(mockSummaries);
  });

  it("returns empty array when response is not ok", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(500));

    const result = await fetchAgentSummaries();

    expect(result).toEqual([]);
  });

  it("returns empty array when fetch throws a network error", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("Connection refused"));

    const result = await fetchAgentSummaries();

    expect(result).toEqual([]);
  });

  it("calls the correct endpoint /api/agents/summary", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse([]));

    await fetchAgentSummaries();

    expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/api/agents/summary");
  });
});

// ---------------------------------------------------------------------------
// fetchLatestNewsletter
// ---------------------------------------------------------------------------

describe("fetchLatestNewsletter", () => {
  const mockItem: NewsletterItem = {
    id: "abc123",
    title: "Edition 47",
    slug: "briefing-47",
    content_type: "newsletter",
    body: "Body content here.",
    published_at: "2026-02-10T00:00:00Z",
  };

  it("returns the parsed newsletter item on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockItem));

    const result = await fetchLatestNewsletter();

    expect(result).toEqual(mockItem);
  });

  it("returns null when response is not ok", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(404));

    const result = await fetchLatestNewsletter();

    expect(result).toBeNull();
  });

  it("returns null when fetch throws a network error", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("Timeout"));

    const result = await fetchLatestNewsletter();

    expect(result).toBeNull();
  });

  it("calls the correct endpoint /api/content/newsletter/latest", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockItem));

    await fetchLatestNewsletter();

    expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/api/content/newsletter/latest");
  });
});

// ---------------------------------------------------------------------------
// fetchNewsletters
// ---------------------------------------------------------------------------

describe("fetchNewsletters", () => {
  const mockPaginated: PaginatedResponse<NewsletterItem> = {
    items: [
      {
        id: "1",
        title: "Test",
        slug: "test",
        content_type: "newsletter",
        body: "Body",
        published_at: "2026-02-10T00:00:00Z",
      },
    ],
    total: 1,
    limit: 20,
    offset: 0,
  };

  it("returns the parsed paginated response on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockPaginated));

    const result = await fetchNewsletters();

    expect(result).toEqual(mockPaginated);
  });

  it("returns empty paginated response when response is not ok", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(500));

    const result = await fetchNewsletters();

    expect(result).toEqual({ items: [], total: 0, limit: 20, offset: 0 });
  });

  it("returns empty paginated response when fetch throws a network error", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("Network error"));

    const result = await fetchNewsletters();

    expect(result).toEqual({ items: [], total: 0, limit: 20, offset: 0 });
  });

  it("builds URL with agent_name param when provided", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockPaginated));

    await fetchNewsletters({ agent_name: "radar" });

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("agent_name=radar");
  });

  it("builds URL with search param when provided", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockPaginated));

    await fetchNewsletters({ search: "fintech LATAM" });

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("search=fintech+LATAM");
  });

  it("builds URL with limit param when provided", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockPaginated));

    await fetchNewsletters({ limit: 10 });

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("limit=10");
  });

  it("builds URL with offset param when provided", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockPaginated));

    await fetchNewsletters({ offset: 20 });

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("offset=20");
  });

  it("builds URL with multiple params combined", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockPaginated));

    await fetchNewsletters({ agent_name: "funding", limit: 5, offset: 10 });

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("agent_name=funding");
    expect(url).toContain("limit=5");
    expect(url).toContain("offset=10");
  });

  it("calls /api/content base endpoint", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockPaginated));

    await fetchNewsletters();

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("/api/content");
  });

  it("includes status=published and excludes ARTICLE content type", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockPaginated));

    await fetchNewsletters();

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("status=published");
    expect(url).toContain("content_type_exclude=ARTICLE");
  });

  it("omits optional params that are not provided (no spurious query string)", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockPaginated));

    await fetchNewsletters({});

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).not.toContain("agent_name");
    expect(url).not.toContain("search");
    expect(url).not.toContain("limit");
    expect(url).not.toContain("offset");
  });
});

// ---------------------------------------------------------------------------
// fetchNewsletterBySlug
// ---------------------------------------------------------------------------

describe("fetchNewsletterBySlug", () => {
  const mockItem: NewsletterItem = {
    id: "xyz",
    title: "Briefing 47",
    slug: "briefing-47-paradoxo-modelo-gratuito",
    content_type: "newsletter",
    body: "Content body.",
    published_at: "2026-02-10T00:00:00Z",
  };

  it("returns the parsed newsletter item on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockItem));

    const result = await fetchNewsletterBySlug("briefing-47-paradoxo-modelo-gratuito");

    expect(result).toEqual(mockItem);
  });

  it("returns null when response is not ok", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(404));

    const result = await fetchNewsletterBySlug("non-existent-slug");

    expect(result).toBeNull();
  });

  it("returns null when fetch throws a network error", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("Abort"));

    const result = await fetchNewsletterBySlug("some-slug");

    expect(result).toBeNull();
  });

  it("builds the URL with the slug appended to /api/content/", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockItem));

    await fetchNewsletterBySlug("briefing-47-paradoxo-modelo-gratuito");

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("/api/content/briefing-47-paradoxo-modelo-gratuito");
  });

  it("handles slugs with special characters by including them verbatim in the URL", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(null, { ok: false, status: 404 }));

    await fetchNewsletterBySlug("slug-with-unicode-cafe");

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("slug-with-unicode-cafe");
  });
});

// ---------------------------------------------------------------------------
// healthCheck
// ---------------------------------------------------------------------------

describe("healthCheck", () => {
  it("returns true when the /health endpoint responds ok", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ status: "ok" }));

    const result = await healthCheck();

    expect(result).toBe(true);
  });

  it("returns false when the /health endpoint responds with non-ok status", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(503));

    const result = await healthCheck();

    expect(result).toBe(false);
  });

  it("returns false when fetch throws a network error", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("ECONNREFUSED"));

    const result = await healthCheck();

    expect(result).toBe(false);
  });

  it("calls the correct /health endpoint", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({}));

    await healthCheck();

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("/health");
  });
});

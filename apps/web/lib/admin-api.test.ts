import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  adminListContent,
  adminGetContent,
  adminCreateContent,
  adminUpdateContent,
  adminDeleteContent,
  adminPublishContent,
  adminUnpublishContent,
  type AdminContent,
  type AdminContentList,
  type ContentCreateData,
  type ContentUpdateData,
} from "@/lib/admin-api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Creates a minimal mock Response compatible with the fetch API. */
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

/** Creates a mock 204 No Content response. */
function mock204Response(): Response {
  return {
    ok: true,
    status: 204,
    json: vi.fn().mockRejectedValue(new SyntaxError("No content")),
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const mockContent: AdminContent = {
  id: "123",
  title: "Test Article",
  slug: "test-article",
  subtitle: null,
  body_md: "# Hello",
  content_type: "ARTICLE",
  agent_name: null,
  review_status: "draft",
  published_at: null,
  created_at: "2026-02-21T00:00:00Z",
  updated_at: null,
  sources: null,
  confidence_dq: null,
  meta_description: null,
};

const mockContentList: AdminContentList = {
  items: [mockContent],
  total: 1,
  limit: 20,
  offset: 0,
};

const ADMIN_PATH = "/api/admin/content";

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
// adminFetch behavior (tested via the public functions)
// ---------------------------------------------------------------------------

describe("adminFetch — shared behavior", () => {
  it("sends Content-Type: application/json header on every request", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminGetContent("test-article");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("throws error with detail from response body on non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(422, { detail: "Validation failed" }));

    await expect(adminGetContent("bad-slug")).rejects.toThrow("Validation failed");
  });

  it("throws generic error message when response body has no detail field", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(500, {}));

    await expect(adminGetContent("some-slug")).rejects.toThrow("Admin API error: 500");
  });

  it("throws generic error message when response body is not valid JSON", async () => {
    const badJsonResponse: Response = {
      ok: false,
      status: 503,
      statusText: "Service Unavailable",
      json: vi.fn().mockRejectedValue(new SyntaxError("Unexpected token")),
    } as unknown as Response;
    vi.mocked(fetch).mockResolvedValue(badJsonResponse);

    await expect(adminGetContent("some-slug")).rejects.toThrow(
      "Admin API error: 503 Service Unavailable",
    );
  });

  it("returns undefined for 204 No Content responses", async () => {
    vi.mocked(fetch).mockResolvedValue(mock204Response());

    const result = await adminDeleteContent("test-article");

    expect(result).toBeUndefined();
  });

  it("calls the correct base URL (/api/admin/content)", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminGetContent("test-article");

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain(ADMIN_PATH);
  });
});

// ---------------------------------------------------------------------------
// adminListContent
// ---------------------------------------------------------------------------

describe("adminListContent", () => {
  it("calls GET with no query string when no params are given", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    await adminListContent();

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(ADMIN_PATH);
    expect(init?.method).toBeUndefined(); // default GET
  });

  it("calls GET with no query string when params object is empty", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    await adminListContent({});

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(ADMIN_PATH);
    expect(url).not.toContain("?");
  });

  it("appends content_type to query string", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    await adminListContent({ content_type: "ARTICLE" });

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("content_type=ARTICLE");
  });

  it("appends status to query string", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    await adminListContent({ status: "published" });

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("status=published");
  });

  it("appends search to query string", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    await adminListContent({ search: "fintech LATAM" });

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("search=fintech");
  });

  it("appends limit to query string", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    await adminListContent({ limit: 10 });

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("limit=10");
  });

  it("appends offset to query string", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    await adminListContent({ offset: 40 });

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("offset=40");
  });

  it("combines multiple params in the query string", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    await adminListContent({ content_type: "NEWSLETTER", status: "draft", limit: 5, offset: 20 });

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("content_type=NEWSLETTER");
    expect(url).toContain("status=draft");
    expect(url).toContain("limit=5");
    expect(url).toContain("offset=20");
  });

  it("returns the parsed AdminContentList on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    const result = await adminListContent();

    expect(result).toEqual(mockContentList);
  });

  it("throws on non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(500, { detail: "Database error" }));

    await expect(adminListContent()).rejects.toThrow("Database error");
  });

  it("omits params that are undefined (no spurious keys in query string)", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContentList));

    await adminListContent({ content_type: "ARTICLE" });

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).not.toContain("status=");
    expect(url).not.toContain("search=");
    expect(url).not.toContain("limit=");
    expect(url).not.toContain("offset=");
  });
});

// ---------------------------------------------------------------------------
// adminGetContent
// ---------------------------------------------------------------------------

describe("adminGetContent", () => {
  it("calls GET /api/admin/content/{slug}", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminGetContent("test-article");

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(`${ADMIN_PATH}/test-article`);
    expect(init?.method).toBeUndefined(); // default GET
  });

  it("returns the parsed AdminContent on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    const result = await adminGetContent("test-article");

    expect(result).toEqual(mockContent);
  });

  it("throws on 404 with detail from response body", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(404, { detail: "Content not found" }));

    await expect(adminGetContent("missing-slug")).rejects.toThrow("Content not found");
  });

  it("appends slug with hyphens and numbers correctly to the URL", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminGetContent("briefing-47-paradoxo-modelo");

    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(`${ADMIN_PATH}/briefing-47-paradoxo-modelo`);
  });
});

// ---------------------------------------------------------------------------
// adminCreateContent
// ---------------------------------------------------------------------------

describe("adminCreateContent", () => {
  const createData: ContentCreateData = {
    title: "New Article",
    body_md: "## Content here",
    content_type: "ARTICLE",
  };

  it("calls POST to /api/admin/content with JSON body", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminCreateContent(createData);

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(ADMIN_PATH);
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify(createData));
  });

  it("sends Content-Type: application/json header", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminCreateContent(createData);

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("returns the created AdminContent on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    const result = await adminCreateContent(createData);

    expect(result).toEqual(mockContent);
  });

  it("serializes all optional fields when provided", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    const fullData: ContentCreateData = {
      title: "Full Article",
      subtitle: "Subtitle here",
      body_md: "## Body",
      content_type: "ARTICLE",
      summary: "A short summary",
      meta_description: "SEO description",
      sources: ["https://source1.com", "https://source2.com"],
    };

    await adminCreateContent(fullData);

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.body).toBe(JSON.stringify(fullData));
  });

  it("throws on non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockErrorResponse(422, { detail: "title field is required" }),
    );

    await expect(adminCreateContent(createData)).rejects.toThrow("title field is required");
  });
});

// ---------------------------------------------------------------------------
// adminUpdateContent
// ---------------------------------------------------------------------------

describe("adminUpdateContent", () => {
  const updateData: ContentUpdateData = {
    title: "Updated Title",
    meta_description: "New SEO description",
  };

  it("calls PATCH /api/admin/content/{slug} with JSON body", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminUpdateContent("test-article", updateData);

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(`${ADMIN_PATH}/test-article`);
    expect(init?.method).toBe("PATCH");
    expect(init?.body).toBe(JSON.stringify(updateData));
  });

  it("sends Content-Type: application/json header", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminUpdateContent("test-article", updateData);

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("returns the updated AdminContent on success", async () => {
    const updatedContent = { ...mockContent, title: "Updated Title" };
    vi.mocked(fetch).mockResolvedValue(mockResponse(updatedContent));

    const result = await adminUpdateContent("test-article", updateData);

    expect(result).toEqual(updatedContent);
  });

  it("allows partial updates with a single field", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    const partialUpdate: ContentUpdateData = { title: "Only Title Changed" };
    await adminUpdateContent("test-article", partialUpdate);

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.body).toBe(JSON.stringify(partialUpdate));
  });

  it("throws on 404 when slug does not exist", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(404, { detail: "Content not found" }));

    await expect(adminUpdateContent("ghost-slug", updateData)).rejects.toThrow("Content not found");
  });

  it("serializes all optional fields when provided", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    const fullUpdate: ContentUpdateData = {
      title: "New Title",
      subtitle: "New Subtitle",
      body_md: "New body",
      content_type: "NEWSLETTER",
      summary: "New summary",
      meta_description: "New meta",
      sources: ["https://updated-source.com"],
    };

    await adminUpdateContent("test-article", fullUpdate);

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.body).toBe(JSON.stringify(fullUpdate));
  });
});

// ---------------------------------------------------------------------------
// adminDeleteContent
// ---------------------------------------------------------------------------

describe("adminDeleteContent", () => {
  it("calls DELETE /api/admin/content/{slug}", async () => {
    vi.mocked(fetch).mockResolvedValue(mock204Response());

    await adminDeleteContent("test-article");

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(`${ADMIN_PATH}/test-article`);
    expect(init?.method).toBe("DELETE");
  });

  it("returns undefined (void) on successful 204 response", async () => {
    vi.mocked(fetch).mockResolvedValue(mock204Response());

    const result = await adminDeleteContent("test-article");

    expect(result).toBeUndefined();
  });

  it("throws on non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(404, { detail: "Content not found" }));

    await expect(adminDeleteContent("missing-slug")).rejects.toThrow("Content not found");
  });

  it("sends Content-Type: application/json header", async () => {
    vi.mocked(fetch).mockResolvedValue(mock204Response());

    await adminDeleteContent("test-article");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });
});

// ---------------------------------------------------------------------------
// adminPublishContent
// ---------------------------------------------------------------------------

describe("adminPublishContent", () => {
  it("calls POST /api/admin/content/{slug}/publish", async () => {
    const publishedContent = {
      ...mockContent,
      review_status: "published",
      published_at: "2026-02-21T10:00:00Z",
    };
    vi.mocked(fetch).mockResolvedValue(mockResponse(publishedContent));

    await adminPublishContent("test-article");

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(`${ADMIN_PATH}/test-article/publish`);
    expect(init?.method).toBe("POST");
  });

  it("returns the updated AdminContent with published state", async () => {
    const publishedContent = {
      ...mockContent,
      review_status: "published",
      published_at: "2026-02-21T10:00:00Z",
    };
    vi.mocked(fetch).mockResolvedValue(mockResponse(publishedContent));

    const result = await adminPublishContent("test-article");

    expect(result.review_status).toBe("published");
    expect(result.published_at).toBe("2026-02-21T10:00:00Z");
  });

  it("sends Content-Type: application/json header", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminPublishContent("test-article");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("throws on non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockErrorResponse(409, { detail: "Content already published" }),
    );

    await expect(adminPublishContent("test-article")).rejects.toThrow("Content already published");
  });

  it("throws on 404 when slug does not exist", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(404, { detail: "Content not found" }));

    await expect(adminPublishContent("ghost-slug")).rejects.toThrow("Content not found");
  });
});

// ---------------------------------------------------------------------------
// adminUnpublishContent
// ---------------------------------------------------------------------------

describe("adminUnpublishContent", () => {
  it("calls POST /api/admin/content/{slug}/unpublish", async () => {
    const unpublishedContent = { ...mockContent, review_status: "draft", published_at: null };
    vi.mocked(fetch).mockResolvedValue(mockResponse(unpublishedContent));

    await adminUnpublishContent("test-article");

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(`${ADMIN_PATH}/test-article/unpublish`);
    expect(init?.method).toBe("POST");
  });

  it("returns the updated AdminContent with unpublished state", async () => {
    const unpublishedContent = {
      ...mockContent,
      review_status: "draft",
      published_at: null,
    };
    vi.mocked(fetch).mockResolvedValue(mockResponse(unpublishedContent));

    const result = await adminUnpublishContent("test-article");

    expect(result.review_status).toBe("draft");
    expect(result.published_at).toBeNull();
  });

  it("sends Content-Type: application/json header", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(mockContent));

    await adminUnpublishContent("test-article");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("throws on non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockErrorResponse(409, { detail: "Content is not published" }),
    );

    await expect(adminUnpublishContent("test-article")).rejects.toThrow("Content is not published");
  });

  it("throws on 404 when slug does not exist", async () => {
    vi.mocked(fetch).mockResolvedValue(mockErrorResponse(404, { detail: "Content not found" }));

    await expect(adminUnpublishContent("ghost-slug")).rejects.toThrow("Content not found");
  });
});

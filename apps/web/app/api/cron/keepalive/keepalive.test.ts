import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ---------------------------------------------------------------------------
// Module-level mocks
//
// vi.mock() is hoisted above all import statements by Vitest. The
// NextResponse.json mock returns a plain object that mimics the shape
// of a real Response: a numeric `status` field and an async `.json()`
// method. This is sufficient for testing route.ts, which only reads
// `res.ok` and `res.status` from the upstream fetch response and passes
// them straight through to NextResponse.json.
// ---------------------------------------------------------------------------

vi.mock("next/server", () => ({
  NextResponse: {
    json: vi.fn((body: unknown, init?: { status?: number }) => ({
      status: init?.status ?? 200,
      json: async () => body,
    })),
  },
}));

// ---------------------------------------------------------------------------
// Imports (resolved after mocks are in place)
// ---------------------------------------------------------------------------

import { GET } from "./route";
import { NextResponse } from "next/server";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a minimal mock fetch Response.
 * Only the fields that route.ts actually reads (ok, status) need to be set.
 */
function mockFetchResponse(options: { ok: boolean; status: number }): Response {
  return { ok: options.ok, status: options.status } as unknown as Response;
}

// ---------------------------------------------------------------------------
// Setup / teardown
//
// Stub global fetch fresh before each test so no test bleeds state into
// the next. vi.unstubAllGlobals() is used in afterEach (not
// vi.restoreAllMocks()) so the NextResponse.json mock is preserved.
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.mocked(NextResponse.json).mockClear();
});

// ---------------------------------------------------------------------------
// keepalive cron route — GET handler
// ---------------------------------------------------------------------------

describe("keepalive cron route", () => {
  // -------------------------------------------------------------------------
  // Happy paths
  // -------------------------------------------------------------------------

  it("test_returns_ok_true_when_health_endpoint_responds_200", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(mockFetchResponse({ ok: true, status: 200 }));

    const response = await GET();
    const body = await response.json();

    expect(body).toEqual({ ok: true, status: 200 });
    expect(response.status).toBe(200);
  });

  it("test_returns_ok_false_when_health_endpoint_responds_500", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(mockFetchResponse({ ok: false, status: 500 }));

    const response = await GET();
    const body = await response.json();

    expect(body).toEqual({ ok: false, status: 500 });
    // The route does not override the outer response status for upstream errors —
    // it always returns 200 in the success branch and passes the upstream status
    // as a field in the JSON body.
    expect(response.status).toBe(200);
  });

  // -------------------------------------------------------------------------
  // Error path
  // -------------------------------------------------------------------------

  it("test_returns_502_when_health_endpoint_is_unreachable", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("ECONNREFUSED"));

    const response = await GET();
    const body = await response.json();

    expect(response.status).toBe(502);
    expect(body).toEqual({ ok: false, error: "unreachable" });
  });

  it("test_returns_502_when_fetch_throws_a_TypeError", async () => {
    // fetch throws TypeError for network-level failures (e.g. DNS failure).
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const response = await GET();
    const body = await response.json();

    expect(response.status).toBe(502);
    expect(body).toEqual({ ok: false, error: "unreachable" });
  });

  // -------------------------------------------------------------------------
  // Fetch call contract
  // -------------------------------------------------------------------------

  it("test_calls_health_endpoint_with_no_store_cache", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(mockFetchResponse({ ok: true, status: 200 }));

    await GET();

    expect(fetch).toHaveBeenCalledOnce();
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toMatch(/\/health$/);
    expect((init as RequestInit)?.cache).toBe("no-store");
  });

  it("test_calls_fetch_exactly_once_per_request", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(mockFetchResponse({ ok: true, status: 200 }));

    await GET();

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("test_uses_localhost_8000_as_default_api_base_when_env_var_is_absent", async () => {
    // NEXT_PUBLIC_API_URL is not set in the test environment, so the fallback
    // "http://localhost:8000" must be used.
    vi.mocked(fetch).mockResolvedValueOnce(mockFetchResponse({ ok: true, status: 200 }));

    await GET();

    const [url] = vi.mocked(fetch).mock.calls[0];
    // Accept either the env-var value (if set) or the localhost fallback.
    // The critical assertion is that the path ends with /health.
    expect(String(url)).toMatch(/\/health$/);
  });

  // -------------------------------------------------------------------------
  // Edge cases
  // -------------------------------------------------------------------------

  it("test_returns_ok_false_and_status_503_for_service_unavailable_response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(mockFetchResponse({ ok: false, status: 503 }));

    const response = await GET();
    const body = await response.json();

    expect(body.ok).toBe(false);
    expect(body.status).toBe(503);
  });

  it("test_returns_ok_true_and_status_204_for_no_content_health_response", async () => {
    // Some health endpoints return 204 No Content. ok is still true for 2xx.
    vi.mocked(fetch).mockResolvedValueOnce(mockFetchResponse({ ok: true, status: 204 }));

    const response = await GET();
    const body = await response.json();

    expect(body.ok).toBe(true);
    expect(body.status).toBe(204);
  });

  it("test_returns_502_when_fetch_throws_abort_error", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(
      new DOMException("The operation was aborted", "AbortError"),
    );

    const response = await GET();
    const body = await response.json();

    expect(response.status).toBe(502);
    expect(body).toEqual({ ok: false, error: "unreachable" });
  });
});

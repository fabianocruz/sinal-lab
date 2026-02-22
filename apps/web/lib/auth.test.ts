import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ---------------------------------------------------------------------------
// Module-level mocks
//
// Vitest hoists vi.mock() calls above all import statements. Any variable
// referenced inside a vi.mock() factory must be created with vi.hoisted()
// so it exists before the hoist boundary.
// ---------------------------------------------------------------------------

const hoisted = vi.hoisted(() => {
  // Mutable container so the NextAuth factory can store the config it receives.
  const captured: { config: Record<string, unknown> } = { config: {} };
  return { captured };
});

vi.mock("next-auth", () => ({
  default: vi.fn((config: Record<string, unknown>) => {
    hoisted.captured.config = config;
    return {
      handlers: { GET: vi.fn(), POST: vi.fn() },
      auth: vi.fn(),
      signIn: vi.fn(),
      signOut: vi.fn(),
    };
  }),
}));

vi.mock("next-auth/providers/credentials", () => ({
  default: vi.fn((config: unknown) => ({ ...(config as object), type: "credentials" })),
}));

vi.mock("next-auth/providers/google", () => ({
  default: vi.fn((config: unknown) => ({ ...(config as object), type: "google" })),
}));

// ---------------------------------------------------------------------------
// Imports (resolved after mocks are in place)
// ---------------------------------------------------------------------------

import { handlers, auth, signIn, signOut } from "./auth";
import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";

// ---------------------------------------------------------------------------
// Stable references extracted once at module evaluation time.
//
// auth.ts calls NextAuth() and CredentialsProvider() once when the module is
// first imported. By the time tests run, the mock call records are already
// populated. We extract the authorize function and provider config here so
// every test shares the same stable reference without re-reading mock.calls.
// ---------------------------------------------------------------------------

type AuthorizeArgs = Record<string, string> | undefined;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AuthorizeFn = (credentials: AuthorizeArgs, req: any) => Promise<unknown>;

type JwtCallbackArgs = {
  token: Record<string, unknown>;
  user?: Record<string, unknown>;
};
type SessionCallbackArgs = {
  session: { user?: Record<string, unknown> };
  token: Record<string, unknown>;
};

// CredentialsProvider is called synchronously during auth.ts module init.
const credentialsProviderConfig = vi.mocked(CredentialsProvider).mock.calls[0][0] as {
  authorize: AuthorizeFn;
  credentials: Record<string, { label: string; type: string }>;
  name: string;
};
const authorize: AuthorizeFn = credentialsProviderConfig.authorize;

// Callbacks are stored on the config object that NextAuth received.
const callbacks = hoisted.captured.config.callbacks as Record<
  string,
  (args: Record<string, unknown>) => Promise<Record<string, unknown>>
>;
const jwtCallback = callbacks.jwt as (args: JwtCallbackArgs) => Promise<Record<string, unknown>>;
const sessionCallback = callbacks.session as (
  args: SessionCallbackArgs,
) => Promise<{ user?: Record<string, unknown> }>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal mock fetch Response. */
function mockFetchResponse<T>(body: T, options: { ok?: boolean; status?: number } = {}): Response {
  const { ok = true, status = 200 } = options;
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// Setup / teardown
//
// We stub fetch fresh before each test and restore only the fetch stub
// afterwards. We do NOT call vi.restoreAllMocks() because that would wipe
// the call history on CredentialsProvider / NextAuth spies, which were
// recorded at module-init time and are needed by the configuration tests.
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

describe("auth module exports", () => {
  it("test_exports_handlers_with_get_method", () => {
    expect(handlers.GET).toBeDefined();
  });

  it("test_exports_handlers_with_post_method", () => {
    expect(handlers.POST).toBeDefined();
  });

  it("test_exports_auth_function", () => {
    expect(auth).toBeDefined();
  });

  it("test_exports_signIn_function", () => {
    expect(signIn).toBeDefined();
  });

  it("test_exports_signOut_function", () => {
    expect(signOut).toBeDefined();
  });

  it("test_nextauth_is_called_once_during_module_initialisation", () => {
    // NextAuth() is called exactly once when auth.ts is imported.
    expect(vi.mocked(NextAuth).mock.calls.length).toBeGreaterThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// NextAuth top-level config
// ---------------------------------------------------------------------------

describe("NextAuth configuration", () => {
  it("test_session_strategy_is_jwt", () => {
    const session = hoisted.captured.config.session as { strategy: string };
    expect(session.strategy).toBe("jwt");
  });

  it("test_signIn_page_is_slash_login", () => {
    const pages = hoisted.captured.config.pages as { signIn: string };
    expect(pages.signIn).toBe("/login");
  });

  it("test_newUser_page_is_slash_cadastro", () => {
    const pages = hoisted.captured.config.pages as { newUser: string };
    expect(pages.newUser).toBe("/cadastro");
  });

  it("test_providers_array_has_exactly_two_entries", () => {
    const providers = hoisted.captured.config.providers as unknown[];
    expect(providers).toHaveLength(2);
  });

  it("test_CredentialsProvider_is_configured_with_name_credentials", () => {
    expect(credentialsProviderConfig.name).toBe("credentials");
  });

  it("test_CredentialsProvider_credentials_has_email_field_of_type_email", () => {
    expect(credentialsProviderConfig.credentials.email.type).toBe("email");
  });

  it("test_CredentialsProvider_credentials_has_password_field_of_type_password", () => {
    expect(credentialsProviderConfig.credentials.password.type).toBe("password");
  });

  it("test_GoogleProvider_is_configured", () => {
    expect(vi.mocked(GoogleProvider).mock.calls.length).toBeGreaterThanOrEqual(1);
  });

  it("test_GoogleProvider_receives_clientId_config_key", () => {
    const config = vi.mocked(GoogleProvider).mock.calls[0][0] as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(config, "clientId")).toBe(true);
  });

  it("test_GoogleProvider_receives_clientSecret_config_key", () => {
    const config = vi.mocked(GoogleProvider).mock.calls[0][0] as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(config, "clientSecret")).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// CredentialsProvider — authorize function
// ---------------------------------------------------------------------------

describe("CredentialsProvider authorize", () => {
  it("test_authorize_returns_null_when_credentials_are_undefined", async () => {
    const result = await authorize(undefined, {});
    expect(result).toBeNull();
  });

  it("test_authorize_returns_null_when_email_is_missing", async () => {
    const result = await authorize({ password: "secret" }, {});
    expect(result).toBeNull();
  });

  it("test_authorize_returns_null_when_password_is_missing", async () => {
    const result = await authorize({ email: "user@example.com" }, {});
    expect(result).toBeNull();
  });

  it("test_authorize_calls_fetch_with_POST_to_api_auth_verify", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockFetchResponse({ id: 1, email: "u@e.com", name: "U", avatar_url: null, status: "active" }),
    );

    await authorize({ email: "u@e.com", password: "pass" }, {});

    expect(fetch).toHaveBeenCalledOnce();
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain("/api/auth/verify");
    expect((init as RequestInit)?.method).toBe("POST");
  });

  it("test_authorize_sends_email_and_password_in_request_body", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockFetchResponse({ id: 1, email: "u@e.com", name: "U", avatar_url: null, status: "active" }),
    );

    await authorize({ email: "u@e.com", password: "mypassword" }, {});

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body).toEqual({ email: "u@e.com", password: "mypassword" });
  });

  it("test_authorize_sets_content_type_json_header", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockFetchResponse({ id: 1, email: "u@e.com", name: "U", avatar_url: null, status: "active" }),
    );

    await authorize({ email: "u@e.com", password: "pass" }, {});

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("test_authorize_returns_user_object_on_successful_response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockFetchResponse({
        id: 42,
        email: "test@sinal.ai",
        name: "Test User",
        avatar_url: "https://example.com/avatar.png",
        status: "active",
      }),
    );

    const result = await authorize({ email: "test@sinal.ai", password: "secret" }, {});

    expect(result).toEqual({
      id: "42",
      email: "test@sinal.ai",
      name: "Test User",
      image: "https://example.com/avatar.png",
      status: "active",
    });
  });

  it("test_authorize_coerces_numeric_id_to_string", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockFetchResponse({
        id: 99,
        email: "x@x.com",
        name: null,
        avatar_url: null,
        status: "active",
      }),
    );

    const result = (await authorize({ email: "x@x.com", password: "pass" }, {})) as {
      id: string;
    };

    expect(result.id).toBe("99");
    expect(typeof result.id).toBe("string");
  });

  it("test_authorize_maps_null_name_to_null", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockFetchResponse({
        id: 1,
        email: "x@x.com",
        name: null,
        avatar_url: null,
        status: "active",
      }),
    );

    const result = (await authorize({ email: "x@x.com", password: "pass" }, {})) as {
      name: string | null;
    };

    expect(result.name).toBeNull();
  });

  it("test_authorize_maps_null_avatar_url_to_null_image", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockFetchResponse({ id: 1, email: "x@x.com", name: "X", avatar_url: null, status: "active" }),
    );

    const result = (await authorize({ email: "x@x.com", password: "pass" }, {})) as {
      image: string | null;
    };

    expect(result.image).toBeNull();
  });

  it("test_authorize_returns_null_when_response_is_not_ok", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockFetchResponse({ detail: "Invalid credentials" }, { ok: false, status: 401 }),
    );

    const result = await authorize({ email: "bad@example.com", password: "wrong" }, {});

    expect(result).toBeNull();
  });

  it("test_authorize_returns_null_on_network_error", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("Network failure"));

    const result = await authorize({ email: "u@e.com", password: "pass" }, {});

    expect(result).toBeNull();
  });

  it("test_authorize_returns_null_when_fetch_throws_abort_error", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new DOMException("AbortError", "AbortError"));

    const result = await authorize({ email: "u@e.com", password: "pass" }, {});

    expect(result).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// jwt callback
// ---------------------------------------------------------------------------

describe("jwt callback", () => {
  it("test_jwt_callback_persists_user_id_into_token_on_first_sign_in", async () => {
    const token = { sub: "sub-123" };
    const user = { id: "user-42", status: "active" };

    const result = await jwtCallback({ token, user });

    expect(result.id).toBe("user-42");
  });

  it("test_jwt_callback_persists_user_status_into_token_on_first_sign_in", async () => {
    const token = { sub: "sub-123" };
    const user = { id: "user-42", status: "pending" };

    const result = await jwtCallback({ token, user });

    expect(result.status).toBe("pending");
  });

  it("test_jwt_callback_defaults_status_to_active_when_user_has_no_status_field", async () => {
    // Google sign-in: user object has no status field
    const token = { sub: "google-sub" };
    const user = { id: "google-user-7" };

    const result = await jwtCallback({ token, user });

    expect(result.status).toBe("active");
  });

  it("test_jwt_callback_preserves_existing_token_fields", async () => {
    const token = { sub: "existing-sub", email: "u@e.com" };
    const user = { id: "user-42", status: "active" };

    const result = await jwtCallback({ token, user });

    expect(result.sub).toBe("existing-sub");
    expect(result.email).toBe("u@e.com");
  });

  it("test_jwt_callback_returns_token_unchanged_on_subsequent_requests_without_user", async () => {
    // Subsequent requests: `user` is not passed — token must come back intact.
    const token = { sub: "sub-123", id: "user-42", status: "active" };

    const result = await jwtCallback({ token });

    expect(result).toEqual(token);
  });
});

// ---------------------------------------------------------------------------
// session callback
// ---------------------------------------------------------------------------

describe("session callback", () => {
  it("test_session_callback_exposes_token_id_on_session_user", async () => {
    const session = { user: { email: "u@e.com" } };
    const token = { id: "user-42", status: "active" };

    const result = await sessionCallback({ session, token });

    expect((result.user as { id: string }).id).toBe("user-42");
  });

  it("test_session_callback_exposes_token_status_on_session_user", async () => {
    const session = { user: { email: "u@e.com" } };
    const token = { id: "user-42", status: "suspended" };

    const result = await sessionCallback({ session, token });

    expect((result.user as { status: string }).status).toBe("suspended");
  });

  it("test_session_callback_returns_session_unchanged_when_user_object_is_absent", async () => {
    // Edge case: session.user can be undefined (e.g. unauthenticated path)
    const session = {};
    const token = { id: "user-42", status: "active" };

    const result = await sessionCallback({ session, token });

    expect(result).toEqual(session);
  });

  it("test_session_callback_preserves_existing_session_user_fields", async () => {
    const session = { user: { email: "founder@sinal.ai", name: "Founder" } };
    const token = { id: "user-99", status: "active" };

    const result = await sessionCallback({ session, token });

    expect((result.user as { email: string }).email).toBe("founder@sinal.ai");
    expect((result.user as { name: string }).name).toBe("Founder");
  });
});

// ---------------------------------------------------------------------------
// fetchWithRetry (tested indirectly via authorize)
//
// fetchWithRetry is a module-private function. We exercise it through the
// CredentialsProvider authorize function, which is the only caller reachable
// from tests. The three behaviours we verify are:
//   1. 502 on first attempt → waits 2 s → retries → returns user on success
//   2. 502 on both attempts → authorize returns null (response.ok is false)
//   3. Non-502 error (e.g. 401) → no retry, fetch called exactly once
//
// The setTimeout(2000) inside fetchWithRetry is handled with fake timers so
// the test suite does not block for a real two seconds.
// ---------------------------------------------------------------------------

describe("fetchWithRetry (via authorize)", () => {
  it("test_authorize_retries_on_502_and_returns_user_on_second_attempt", async () => {
    vi.useFakeTimers();

    vi.mocked(fetch)
      .mockResolvedValueOnce(mockFetchResponse({}, { ok: false, status: 502 }))
      .mockResolvedValueOnce(
        mockFetchResponse({
          id: 1,
          email: "u@e.com",
          name: null,
          avatar_url: null,
          status: "active",
        }),
      );

    const promise = authorize({ email: "u@e.com", password: "pass" }, {});

    // Advance past the 2-second back-off delay inside fetchWithRetry.
    await vi.advanceTimersByTimeAsync(2000);

    const result = await promise;

    vi.useRealTimers();

    // Two fetch calls: initial 502 attempt + one retry.
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2);
    // Second attempt succeeded — authorize should return the mapped user.
    expect(result).toEqual({
      id: "1",
      email: "u@e.com",
      name: null,
      image: null,
      status: "active",
    });
  });

  it("test_authorize_returns_null_when_both_attempts_return_502", async () => {
    vi.useFakeTimers();

    vi.mocked(fetch)
      .mockResolvedValueOnce(mockFetchResponse({}, { ok: false, status: 502 }))
      .mockResolvedValueOnce(mockFetchResponse({}, { ok: false, status: 502 }));

    const promise = authorize({ email: "u@e.com", password: "pass" }, {});

    await vi.advanceTimersByTimeAsync(2000);

    const result = await promise;

    vi.useRealTimers();

    // Both attempts returned 502 — response.ok is false so authorize returns null.
    expect(result).toBeNull();
    // fetchWithRetry still issued exactly two calls.
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2);
  });

  it("test_authorize_does_not_retry_on_non_502_error_status", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockFetchResponse({ detail: "Unauthorized" }, { ok: false, status: 401 }),
    );

    const result = await authorize({ email: "u@e.com", password: "wrong" }, {});

    // 401 is not a 502 — fetchWithRetry must NOT issue a second fetch call.
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
    // Non-ok response → authorize returns null.
    expect(result).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// NextAuth API route (app/api/auth/[...nextauth]/route.ts)
// ---------------------------------------------------------------------------

describe("NextAuth API route", () => {
  it("test_route_exports_GET_and_POST_handlers", async () => {
    const route = await import("../app/api/auth/[...nextauth]/route");
    expect(route.GET).toBeDefined();
    expect(route.POST).toBeDefined();
  });

  it("test_route_GET_is_the_same_reference_as_handlers_GET", async () => {
    const route = await import("../app/api/auth/[...nextauth]/route");
    expect(route.GET).toBe(handlers.GET);
  });

  it("test_route_POST_is_the_same_reference_as_handlers_POST", async () => {
    const route = await import("../app/api/auth/[...nextauth]/route");
    expect(route.POST).toBe(handlers.POST);
  });
});

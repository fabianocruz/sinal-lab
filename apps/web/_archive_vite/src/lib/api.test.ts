import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  submitWaitlist,
  fetchWaitlistCount,
  fetchAgentSummaries,
  fetchLatestNewsletter,
  healthCheck,
  type WaitlistSignupData,
  type WaitlistSignupResponse,
  type AgentSummary,
  type NewsletterItem,
} from "./api";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("API Client", () => {
  beforeEach(() => {
    mockFetch.mockClear();
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("submitWaitlist", () => {
    it("should successfully submit waitlist signup", async () => {
      const mockResponse: WaitlistSignupResponse = {
        message: "Voce esta na lista! Fique de olho no seu email.",
        email: "test@example.com",
        position: 248,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const data: WaitlistSignupData = {
        email: "test@example.com",
        name: "Test User",
      };

      const result = await submitWaitlist(data);

      expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/waitlist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      expect(result).toEqual(mockResponse);
    });

    it("should throw error when API returns error response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Email ja cadastrado na waitlist." }),
      });

      const data: WaitlistSignupData = {
        email: "duplicate@example.com",
      };

      await expect(submitWaitlist(data)).rejects.toThrow("Email ja cadastrado na waitlist.");
    });

    it("should handle malformed error response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => {
          throw new Error("Invalid JSON");
        },
      });

      const data: WaitlistSignupData = {
        email: "test@example.com",
      };

      await expect(submitWaitlist(data)).rejects.toThrow("Failed to submit to waitlist");
    });

    it("should submit with all optional fields", async () => {
      const mockResponse: WaitlistSignupResponse = {
        message: "Success",
        email: "full@example.com",
        position: 300,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const data: WaitlistSignupData = {
        email: "full@example.com",
        name: "Full Name",
        company: "Tech Corp",
        role: "CTO",
      };

      const result = await submitWaitlist(data);

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify(data),
        }),
      );
    });
  });

  describe("fetchWaitlistCount", () => {
    it("should fetch waitlist count successfully", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ count: 350 }),
      });

      const result = await fetchWaitlistCount();

      expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/waitlist/count");
      expect(result).toBe(350);
    });

    it("should return fallback when API fails", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
      });

      const result = await fetchWaitlistCount();

      expect(result).toBe(247);
      expect(console.warn).toHaveBeenCalledWith("Failed to fetch waitlist count, using fallback");
    });

    it("should return fallback when network error occurs", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await fetchWaitlistCount();

      expect(result).toBe(247);
      expect(console.warn).toHaveBeenCalledWith(
        "Error fetching waitlist count:",
        expect.any(Error),
      );
    });

    it("should use fallback when count is missing in response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const result = await fetchWaitlistCount();

      expect(result).toBe(247);
    });
  });

  describe("fetchAgentSummaries", () => {
    it("should fetch agent summaries successfully", async () => {
      const mockAgents: AgentSummary[] = [
        {
          agent_name: "SINTESE",
          last_run: "2026-02-17T10:00:00Z",
          status: "active",
          items_processed: 150,
          avg_confidence: 0.85,
          sources: 20,
          error_count: 2,
        },
        {
          agent_name: "RADAR",
          last_run: null,
          status: "idle",
          items_processed: 0,
          avg_confidence: 0,
          sources: 0,
          error_count: 0,
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAgents,
      });

      const result = await fetchAgentSummaries();

      expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/agents/summary");
      expect(result).toEqual(mockAgents);
    });

    it("should return empty array when API fails", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
      });

      const result = await fetchAgentSummaries();

      expect(result).toEqual([]);
      expect(console.warn).toHaveBeenCalledWith("Failed to fetch agent summaries");
    });

    it("should return empty array on network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await fetchAgentSummaries();

      expect(result).toEqual([]);
    });
  });

  describe("fetchLatestNewsletter", () => {
    it("should fetch latest newsletter successfully", async () => {
      const mockNewsletter: NewsletterItem = {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Briefing #01",
        slug: "briefing-01",
        content_type: "newsletter",
        body: "# Newsletter content here",
        published_at: "2026-02-17T08:00:00Z",
        metadata: {
          author: "SINTESE",
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockNewsletter,
      });

      const result = await fetchLatestNewsletter();

      expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/content/newsletter/latest");
      expect(result).toEqual(mockNewsletter);
    });

    it("should return null when API fails", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
      });

      const result = await fetchLatestNewsletter();

      expect(result).toBeNull();
      expect(console.warn).toHaveBeenCalledWith("Failed to fetch latest newsletter");
    });

    it("should return null on network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await fetchLatestNewsletter();

      expect(result).toBeNull();
    });
  });

  describe("healthCheck", () => {
    it("should return true when API is healthy", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
      });

      const result = await healthCheck();

      expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/health", {
        method: "GET",
      });
      expect(result).toBe(true);
    });

    it("should return false when API returns error", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
      });

      const result = await healthCheck();

      expect(result).toBe(false);
    });

    it("should return false on network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await healthCheck();

      expect(result).toBe(false);
      expect(console.warn).toHaveBeenCalledWith("API health check failed:", expect.any(Error));
    });
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Company } from "@/lib/company";

// ---------------------------------------------------------------------------
// Mock fetchCompanies before importing the component
// ---------------------------------------------------------------------------

const mockFetchCompanies = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchCompanies: (...args: unknown[]) => mockFetchCompanies(...args),
}));

// Dynamic import to pick up mock
const { default: MapaHighlight } = await import("@/components/landing/MapaHighlight");

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const sampleCompany: Company = {
  id: "1",
  name: "TestCo",
  slug: "testco",
  description: "A test company",
  short_description: "Test startup",
  sector: "Fintech",
  sub_sector: null,
  city: "São Paulo",
  state: "SP",
  country: "Brasil",
  tags: ["fintech"],
  tech_stack: null,
  founded_date: "2024-01-01",
  team_size: 50,
  business_model: "B2B",
  funding_stage: "Seed",
  total_funding_usd: 5_000_000,
  is_trending: false,
  website: "https://testco.com",
  github_url: null,
  linkedin_url: null,
  twitter_url: null,
  source_count: 3,
  status: "active",
  created_at: "2026-02-01T00:00:00Z",
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MapaHighlight", () => {
  beforeEach(() => {
    mockFetchCompanies.mockReset();
  });

  it("renders null when no companies returned", async () => {
    mockFetchCompanies.mockResolvedValue({ items: [], total: 0, limit: 6, offset: 0 });
    const result = await MapaHighlight();
    expect(result).toBeNull();
  });

  it("renders section with companies", async () => {
    mockFetchCompanies.mockResolvedValue({
      items: [sampleCompany],
      total: 1,
      limit: 6,
      offset: 0,
    });
    const Component = await MapaHighlight();
    render(Component!);
    expect(screen.getByText("TestCo")).toBeInTheDocument();
  });

  it("renders MERCADO agent label", async () => {
    mockFetchCompanies.mockResolvedValue({
      items: [sampleCompany],
      total: 1,
      limit: 6,
      offset: 0,
    });
    const Component = await MapaHighlight();
    render(Component!);
    expect(screen.getByText("MERCADO")).toBeInTheDocument();
  });

  it("renders section heading", async () => {
    mockFetchCompanies.mockResolvedValue({
      items: [sampleCompany],
      total: 1,
      limit: 6,
      offset: 0,
    });
    const Component = await MapaHighlight();
    render(Component!);
    expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
  });

  it("renders CTA link to /startups", async () => {
    mockFetchCompanies.mockResolvedValue({
      items: [sampleCompany],
      total: 1,
      limit: 6,
      offset: 0,
    });
    const Component = await MapaHighlight();
    render(Component!);
    const ctaLink = screen.getByText(/Explorar o mapa completo/);
    expect(ctaLink.closest("a")).toHaveAttribute("href", "/startups");
  });

  it("renders sector pills", async () => {
    mockFetchCompanies.mockResolvedValue({
      items: [sampleCompany],
      total: 1,
      limit: 6,
      offset: 0,
    });
    const Component = await MapaHighlight();
    render(Component!);
    expect(screen.getAllByText("AI / ML").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("SaaS").length).toBeGreaterThanOrEqual(1);
  });

  it("renders country distribution sidebar", async () => {
    mockFetchCompanies.mockResolvedValue({
      items: [sampleCompany],
      total: 1,
      limit: 6,
      offset: 0,
    });
    const Component = await MapaHighlight();
    render(Component!);
    expect(screen.getByText("Brasil")).toBeInTheDocument();
    expect(screen.getByText("Argentina")).toBeInTheDocument();
  });

  it("calls fetchCompanies with limit 6", async () => {
    mockFetchCompanies.mockResolvedValue({ items: [], total: 0, limit: 6, offset: 0 });
    await MapaHighlight();
    expect(mockFetchCompanies).toHaveBeenCalledWith({ limit: 6 });
  });

  it("renders company card linking to detail page", async () => {
    mockFetchCompanies.mockResolvedValue({
      items: [sampleCompany],
      total: 1,
      limit: 6,
      offset: 0,
    });
    const Component = await MapaHighlight();
    render(Component!);
    const link = screen.getByText("TestCo").closest("a");
    expect(link).toHaveAttribute("href", "/startup/testco");
  });
});

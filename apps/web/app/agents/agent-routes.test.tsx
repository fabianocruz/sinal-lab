import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import RadarSlugLoading from "@/app/radar/[slug]/loading";
import FundingSlugLoading from "@/app/funding/[slug]/loading";
import CodigoSlugLoading from "@/app/codigo/[slug]/loading";
import MercadoSlugLoading from "@/app/mercado/[slug]/loading";

// ---------------------------------------------------------------------------
// All 4 agent loading components share the same skeleton structure.
// We test each renders correctly, then run structural assertions on one
// representative to keep the suite DRY.
// ---------------------------------------------------------------------------

const AGENT_LOADINGS = [
  { name: "RadarSlugLoading", Component: RadarSlugLoading },
  { name: "FundingSlugLoading", Component: FundingSlugLoading },
  { name: "CodigoSlugLoading", Component: CodigoSlugLoading },
  { name: "MercadoSlugLoading", Component: MercadoSlugLoading },
] as const;

// ---------------------------------------------------------------------------
// Smoke tests — all 4 agent loading components
// ---------------------------------------------------------------------------

describe.each(AGENT_LOADINGS)("$name", ({ Component }) => {
  it("renders without crashing", () => {
    expect(() => render(<Component />)).not.toThrow();
  });

  it("has pt-[72px] navbar offset", () => {
    const { container } = render(<Component />);
    const outer = container.firstElementChild as HTMLElement;
    expect(outer.className).toContain("pt-[72px]");
  });

  it("contains multiple animate-pulse skeleton elements", () => {
    const { container } = render(<Component />);
    const pulsingElements = container.querySelectorAll(".animate-pulse");
    expect(pulsingElements.length).toBeGreaterThan(5);
  });

  it("renders an article element", () => {
    const { container } = render(<Component />);
    expect(container.querySelector("article")).toBeInTheDocument();
  });

  it("renders a header inside the article", () => {
    const { container } = render(<Component />);
    const article = container.querySelector("article");
    expect(article!.querySelector("header")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Structural assertions — representative component (RadarSlugLoading)
// All 4 share identical markup, so testing one in depth covers all.
// ---------------------------------------------------------------------------

describe("Agent slug loading skeleton structure (RadarSlugLoading)", () => {
  it("renders back-link skeleton (mb-8 h-4 w-32)", () => {
    const { container } = render(<RadarSlugLoading />);
    const backLink = container.querySelector(".mb-8.h-4.w-32.animate-pulse");
    expect(backLink).toBeInTheDocument();
  });

  it("renders agent pill and date skeletons in header flex row", () => {
    const { container } = render(<RadarSlugLoading />);
    const agentBone = container.querySelector(".h-4.w-20.animate-pulse");
    const dateBone = container.querySelector(".h-4.w-32.animate-pulse");
    expect(agentBone).toBeInTheDocument();
    expect(dateBone).toBeInTheDocument();
  });

  it("renders title skeletons (h-10 full width and 3/4 width)", () => {
    const { container } = render(<RadarSlugLoading />);
    const titleFull = container.querySelector(".h-10.w-full.animate-pulse");
    const titlePartial = container.querySelector(".h-10.w-3\\/4.animate-pulse");
    expect(titleFull).toBeInTheDocument();
    expect(titlePartial).toBeInTheDocument();
  });

  it("renders subtitle skeleton (h-5 w-2/3)", () => {
    const { container } = render(<RadarSlugLoading />);
    const subtitle = container.querySelector("header .h-5.w-2\\/3.animate-pulse");
    expect(subtitle).toBeInTheDocument();
  });

  it("renders avatar circle skeleton (h-8 w-8 rounded-full)", () => {
    const { container } = render(<RadarSlugLoading />);
    const avatar = container.querySelector(".h-8.w-8.rounded-full.animate-pulse");
    expect(avatar).toBeInTheDocument();
  });

  it("renders 5 body line skeletons with inline width styles", () => {
    const { container } = render(<RadarSlugLoading />);
    const bodyLines = container.querySelectorAll(".space-y-4 .h-5.animate-pulse");
    expect(bodyLines).toHaveLength(5);
    bodyLines.forEach((line) => {
      expect((line as HTMLElement).style.width).toMatch(/^\d+%$/);
    });
  });

  it("body line widths follow the formula 85 + (i % 3) * 5", () => {
    const { container } = render(<RadarSlugLoading />);
    const bodyLines = container.querySelectorAll(".space-y-4 .h-5.animate-pulse");
    const widths = Array.from(bodyLines).map((el) => (el as HTMLElement).style.width);
    // 85 + (0%3)*5=85, 85+(1%3)*5=90, 85+(2%3)*5=95, 85+(3%3)*5=85, 85+(4%3)*5=90
    expect(widths).toEqual(["85%", "90%", "95%", "85%", "90%"]);
  });

  it("header has border-bottom separator", () => {
    const { container } = render(<RadarSlugLoading />);
    const header = container.querySelector("header");
    expect(header!.className).toContain("border-b");
  });
});

// ---------------------------------------------------------------------------
// generateAgentContentMetadata — unit tests
// ---------------------------------------------------------------------------

describe("generateAgentContentMetadata", () => {
  let generateAgentContentMetadata: typeof import("@/lib/agent-content").generateAgentContentMetadata;

  beforeEach(async () => {
    vi.resetModules();
  });

  it("returns 'Conteudo nao encontrado' when API returns null", async () => {
    vi.doMock("@/lib/api", () => ({
      fetchNewsletterBySlug: vi.fn().mockResolvedValue(null),
    }));

    const mod = await import("@/lib/agent-content");
    generateAgentContentMetadata = mod.generateAgentContentMetadata;

    const metadata = await generateAgentContentMetadata("radar", "nonexistent-slug");
    expect(metadata.title).toBe("Conteúdo não encontrado");
  });

  it("includes agent code in title when API returns content", async () => {
    vi.doMock("@/lib/api", () => ({
      fetchNewsletterBySlug: vi.fn().mockResolvedValue({
        id: "test-id",
        title: "Test Article",
        slug: "test-article",
        content_type: "ANALYSIS",
        review_status: "published",
        agent_name: "radar",
        subtitle: "Test subtitle",
        summary: null,
        meta_description: null,
        published_at: "2026-02-10T00:00:00Z",
      }),
    }));

    const mod = await import("@/lib/agent-content");
    generateAgentContentMetadata = mod.generateAgentContentMetadata;

    const metadata = await generateAgentContentMetadata("radar", "test-article");
    expect(metadata.title).toContain("Test Article");
    expect(metadata.title).toContain("RADAR");
    expect(metadata.title).toContain("Sinal");
  });

  it("uses subtitle as description when available", async () => {
    vi.doMock("@/lib/api", () => ({
      fetchNewsletterBySlug: vi.fn().mockResolvedValue({
        id: "test-id",
        title: "Test Article",
        slug: "test-article",
        content_type: "ANALYSIS",
        review_status: "published",
        agent_name: "funding",
        subtitle: "Funding subtitle",
        summary: "Funding summary",
        meta_description: "Funding meta",
        published_at: null,
      }),
    }));

    const mod = await import("@/lib/agent-content");
    generateAgentContentMetadata = mod.generateAgentContentMetadata;

    const metadata = await generateAgentContentMetadata("funding", "test-article");
    expect(metadata.description).toBe("Funding subtitle");
  });

  it("falls back to summary when subtitle is null", async () => {
    vi.doMock("@/lib/api", () => ({
      fetchNewsletterBySlug: vi.fn().mockResolvedValue({
        id: "test-id",
        title: "Test Article",
        slug: "test-article",
        content_type: "ANALYSIS",
        review_status: "published",
        subtitle: null,
        summary: "A summary",
        meta_description: "Meta desc",
        published_at: null,
      }),
    }));

    const mod = await import("@/lib/agent-content");
    generateAgentContentMetadata = mod.generateAgentContentMetadata;

    const metadata = await generateAgentContentMetadata("codigo", "test-article");
    expect(metadata.description).toBe("A summary");
  });

  it("falls back to meta_description when subtitle and summary are null", async () => {
    vi.doMock("@/lib/api", () => ({
      fetchNewsletterBySlug: vi.fn().mockResolvedValue({
        id: "test-id",
        title: "Test Article",
        slug: "test-article",
        content_type: "ANALYSIS",
        review_status: "published",
        subtitle: null,
        summary: null,
        meta_description: "Meta description only",
        published_at: null,
      }),
    }));

    const mod = await import("@/lib/agent-content");
    generateAgentContentMetadata = mod.generateAgentContentMetadata;

    const metadata = await generateAgentContentMetadata("mercado", "test-article");
    expect(metadata.description).toBe("Meta description only");
  });

  it("sets openGraph type to article", async () => {
    vi.doMock("@/lib/api", () => ({
      fetchNewsletterBySlug: vi.fn().mockResolvedValue({
        id: "test-id",
        title: "OG Test",
        slug: "og-test",
        content_type: "ANALYSIS",
        review_status: "published",
        subtitle: "Sub",
        summary: null,
        meta_description: null,
        published_at: "2026-02-10T00:00:00Z",
      }),
    }));

    const mod = await import("@/lib/agent-content");
    generateAgentContentMetadata = mod.generateAgentContentMetadata;

    const metadata = await generateAgentContentMetadata("radar", "og-test");
    expect(metadata.openGraph).toBeDefined();
    expect((metadata.openGraph as Record<string, unknown>).type).toBe("article");
  });

  it("includes publishedTime in openGraph when available", async () => {
    vi.doMock("@/lib/api", () => ({
      fetchNewsletterBySlug: vi.fn().mockResolvedValue({
        id: "test-id",
        title: "Date Test",
        slug: "date-test",
        content_type: "ANALYSIS",
        review_status: "published",
        subtitle: "Sub",
        summary: null,
        meta_description: null,
        published_at: "2026-02-15T12:00:00Z",
      }),
    }));

    const mod = await import("@/lib/agent-content");
    generateAgentContentMetadata = mod.generateAgentContentMetadata;

    const metadata = await generateAgentContentMetadata("radar", "date-test");
    expect((metadata.openGraph as Record<string, unknown>).publishedTime).toBe(
      "2026-02-15T12:00:00Z",
    );
  });
});

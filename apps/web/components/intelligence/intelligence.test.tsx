import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(() => ({ data: null, status: "unauthenticated" })),
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/components/newsletter/MarkdownRenderer", () => ({
  default: ({ content }: { content: string }) => <div data-testid="markdown">{content}</div>,
}));

vi.mock("@/components/newsletter/HeroImage", () => ({
  default: () => <div data-testid="hero-image" />,
}));

vi.mock("@/components/newsletter/SourcesList", () => ({
  default: ({ sources }: { sources: string[] }) => (
    <div data-testid="sources-list">{sources.length} sources</div>
  ),
}));

import IntelligenceContent from "./IntelligenceContent";
import type { ContentApiItem } from "@/lib/newsletter";

const MOCK_ITEM: ContentApiItem = {
  id: "intel-1",
  title: "DevTools LATAM: 100 startups mapeadas",
  slug: "devtools-market-intelligence-mar-2026",
  content_type: "INTELLIGENCE",
  summary: "Mapeamento completo das startups de developer tools.",
  review_status: "published",
  published_at: "2026-03-15T10:00:00Z",
  author_name: "Fabiano Cruz",
  subtitle: "O maior mapeamento de developer tools da America Latina.",
  body_md: "# Introducao\n\nConteudo do relatorio completo aqui.",
  sources: ["https://example.com/source1", "https://example.com/source2"],
  metadata_: null,
};

// ===========================================================================
// IntelligenceContent
// ===========================================================================

describe("IntelligenceContent", () => {
  it("renders the report title", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    expect(screen.getByText("DevTools LATAM: 100 startups mapeadas")).toBeInTheDocument();
  });

  it("renders the Intelligence badge", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    expect(screen.getByText("Intelligence")).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    expect(
      screen.getByText("O maior mapeamento de developer tools da America Latina."),
    ).toBeInTheDocument();
  });

  it("renders author name", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    expect(screen.getByText("Fabiano Cruz")).toBeInTheDocument();
  });

  it("renders Market Intelligence label", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    expect(screen.getByText("Market Intelligence")).toBeInTheDocument();
  });

  it("renders the published date", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    expect(screen.getByText(/15 de mar/i)).toBeInTheDocument();
  });

  it("renders full body content without gating", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    const markdown = screen.getByTestId("markdown");
    expect(markdown.textContent).toContain("Conteudo do relatorio completo aqui.");
  });

  it("renders sources list when sources exist", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    expect(screen.getByTestId("sources-list")).toBeInTheDocument();
  });

  it("does not render sources list when empty", () => {
    render(<IntelligenceContent item={{ ...MOCK_ITEM, sources: [] }} />);
    expect(screen.queryByTestId("sources-list")).not.toBeInTheDocument();
  });

  it("renders back link to /intelligence", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    const backLinks = screen.getAllByText(/Voltar aos Relatorios/i);
    expect(backLinks.length).toBeGreaterThanOrEqual(1);
  });

  it("renders footer link to all reports", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    expect(screen.getByText(/Ver todos os relatorios/i)).toBeInTheDocument();
  });

  it("renders default author when author_name is null", () => {
    render(<IntelligenceContent item={{ ...MOCK_ITEM, author_name: null }} />);
    expect(screen.getByText("Sinal Intelligence")).toBeInTheDocument();
  });

  it("renders hero image component", () => {
    render(<IntelligenceContent item={MOCK_ITEM} />);
    expect(screen.getByTestId("hero-image")).toBeInTheDocument();
  });
});

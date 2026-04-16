import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(() => ({ data: null, status: "unauthenticated" })),
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/intelligence/devtools-market-intelligence-mar-2026"),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
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

import { useSession } from "next-auth/react";
import IntelligenceContent from "./IntelligenceContent";
import IntelligenceGate from "./IntelligenceGate";
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

// ===========================================================================
// IntelligenceGate
// ===========================================================================

describe("IntelligenceGate — unauthenticated", () => {
  it("shows preview content for unauthenticated users", () => {
    vi.mocked(useSession).mockReturnValue({ data: null, status: "unauthenticated" } as ReturnType<
      typeof useSession
    >);
    render(<IntelligenceGate content="# Introducao\n\nConteudo do relatorio completo aqui." />);
    expect(screen.getByTestId("intelligence-gate")).toBeInTheDocument();
  });

  it("renders the gate sign-up prompt for unauthenticated users", () => {
    vi.mocked(useSession).mockReturnValue({ data: null, status: "unauthenticated" } as ReturnType<
      typeof useSession
    >);
    render(<IntelligenceGate content="Conteudo aqui." />);
    expect(screen.getByText(/Continue lendo gratuitamente/i)).toBeInTheDocument();
  });

  it("renders sign-up link for unauthenticated users", () => {
    vi.mocked(useSession).mockReturnValue({ data: null, status: "unauthenticated" } as ReturnType<
      typeof useSession
    >);
    render(<IntelligenceGate content="Conteudo aqui." />);
    expect(screen.getByText(/Criar conta gratuita/i)).toBeInTheDocument();
  });

  it("renders login link for unauthenticated users", () => {
    vi.mocked(useSession).mockReturnValue({ data: null, status: "unauthenticated" } as ReturnType<
      typeof useSession
    >);
    render(<IntelligenceGate content="Conteudo aqui." />);
    expect(screen.getByText(/Ja tenho conta/i)).toBeInTheDocument();
  });
});

describe("IntelligenceGate — authenticated", () => {
  it("shows full content for authenticated users without gate wrapper", () => {
    vi.mocked(useSession).mockReturnValue({
      data: { user: { name: "Test" }, expires: "2099-01-01" },
      status: "authenticated",
    } as ReturnType<typeof useSession>);
    render(<IntelligenceGate content="# Introducao\n\nConteudo do relatorio completo aqui." />);
    expect(screen.queryByTestId("intelligence-gate")).not.toBeInTheDocument();
    const markdown = screen.getByTestId("markdown");
    expect(markdown.textContent).toContain("Conteudo do relatorio completo aqui.");
  });

  it("does not render sign-up prompt for authenticated users", () => {
    vi.mocked(useSession).mockReturnValue({
      data: { user: { name: "Test" }, expires: "2099-01-01" },
      status: "authenticated",
    } as ReturnType<typeof useSession>);
    render(<IntelligenceGate content="Conteudo aqui." />);
    expect(screen.queryByText(/Continue lendo gratuitamente/i)).not.toBeInTheDocument();
  });
});

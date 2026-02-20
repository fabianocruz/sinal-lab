import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { useSession } from "next-auth/react";

import GatedOverlay from "@/components/newsletter/GatedOverlay";
import NewsletterContent from "@/components/newsletter/NewsletterContent";
import { Newsletter } from "@/lib/newsletter";
import { AGENT_PERSONAS } from "@/lib/constants";

// ---------------------------------------------------------------------------
// Module-level mock — overrides the global setup.tsx mock for this file only.
// useSession must be a vi.fn() so individual tests can call .mockReturnValue().
// vi.mock() calls are hoisted by Vitest, so this runs before any imports.
// ---------------------------------------------------------------------------
vi.mock("next-auth/react", () => ({
  useSession: vi.fn(() => ({ data: null, status: "unauthenticated" })),
  SessionProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ---------------------------------------------------------------------------
// Shared test fixtures
// ---------------------------------------------------------------------------

/**
 * Mock newsletter with 10 paragraphs so previewCount is deterministic:
 *   Math.ceil(10 * 0.3) = 3 visible, 7 gated.
 */
const mockNewsletter: Newsletter = {
  slug: "test-edition",
  edition: 99,
  date: "20 Jan 2026",
  dateISO: "2026-01-20",
  title: "Test Newsletter Title",
  subtitle: "Test subtitle for the newsletter",
  agent: "sintese",
  agentLabel: "SINTESE",
  body: [
    "Paragraph one content.",
    "Paragraph two content.",
    "Paragraph three content.",
    "Paragraph four content.",
    "Paragraph five content.",
    "Paragraph six content.",
    "Paragraph seven content.",
    "Paragraph eight content.",
    "Paragraph nine content.",
    "Paragraph ten content.",
  ].join("\n\n"),
  dqScore: "A",
  likes: 0,
  gradientIndex: 1,
};

/**
 * Newsletter with dqScore: null to verify the DQ badge is conditionally rendered.
 */
const mockNewsletterNoDq: Newsletter = {
  ...mockNewsletter,
  slug: "test-edition-no-dq",
  dqScore: null,
};

/**
 * Newsletter whose entire body fits inside the preview window (1 paragraph):
 *   Math.ceil(1 * 0.3) = 1, so remainingParagraphs.length === 0.
 * This activates the "footer note always visible" branch even when unauthenticated.
 */
const mockNewsletterShortBody: Newsletter = {
  ...mockNewsletter,
  slug: "test-edition-short",
  body: "Only one paragraph.",
};

// ---------------------------------------------------------------------------
// Helper: query the footer note paragraph whose textContent contains "Sinal e
// gerado por 5 agentes". The paragraph mixes a <strong> child and plain text
// nodes, so a regex matcher will not find it — we must match by textContent.
// ---------------------------------------------------------------------------

function queryFooterNote(): HTMLElement | null {
  return screen.queryByText(
    (_content, element) =>
      element?.tagName === "P" &&
      (element.textContent ?? "").includes("e gerado por 5 agentes de IA"),
  );
}

// ---------------------------------------------------------------------------
// Helper: override useSession for authenticated state
// ---------------------------------------------------------------------------

function mockAuthenticated() {
  vi.mocked(useSession).mockReturnValue({
    data: { user: { name: "Test User", email: "test@test.com" }, expires: "" },
    status: "authenticated",
    update: vi.fn(),
  });
}

function mockUnauthenticated() {
  vi.mocked(useSession).mockReturnValue({
    data: null,
    status: "unauthenticated",
    update: vi.fn(),
  });
}

// ---------------------------------------------------------------------------
// GatedOverlay
// ---------------------------------------------------------------------------

describe("GatedOverlay", () => {
  it("test_gatedoverlay_render_shows_continue_lendo_heading", () => {
    render(<GatedOverlay />);

    expect(screen.getByRole("heading", { name: "Continue lendo" })).toBeInTheDocument();
  });

  it("test_gatedoverlay_render_shows_description_text", () => {
    render(<GatedOverlay />);

    expect(
      screen.getByText("Crie sua conta gratuita para acessar todas as edicoes do Sinal."),
    ).toBeInTheDocument();
  });

  it("test_gatedoverlay_render_shows_criar_conta_link_to_cadastro", () => {
    render(<GatedOverlay />);

    const link = screen.getByRole("link", { name: "Criar conta gratuita" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/cadastro");
  });

  it("test_gatedoverlay_render_shows_ja_tenho_conta_link_to_login", () => {
    render(<GatedOverlay />);

    const link = screen.getByRole("link", { name: "Ja tenho conta" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/login");
  });

  it("test_gatedoverlay_render_shows_disclaimer_text", () => {
    render(<GatedOverlay />);

    expect(screen.getByText("Gratis. Sem spam. Cancele quando quiser.")).toBeInTheDocument();
  });

  it("test_gatedoverlay_render_has_gradient_fade_div_with_aria_hidden", () => {
    const { container } = render(<GatedOverlay />);

    const gradientDiv = container.querySelector('[aria-hidden="true"]');
    expect(gradientDiv).toBeInTheDocument();
  });

  it("test_gatedoverlay_render_gradient_div_has_linear_gradient_style", () => {
    const { container } = render(<GatedOverlay />);

    const gradientDiv = container.querySelector('[aria-hidden="true"]') as HTMLElement;
    expect(gradientDiv.style.background).toContain("linear-gradient");
  });

  it("test_gatedoverlay_render_criar_conta_and_ja_tenho_conta_are_distinct_links", () => {
    render(<GatedOverlay />);

    const links = screen.getAllByRole("link");
    const hrefs = links.map((l) => l.getAttribute("href"));
    expect(hrefs).toContain("/cadastro");
    expect(hrefs).toContain("/login");
  });
});

// ---------------------------------------------------------------------------
// NewsletterContent — unauthenticated
// ---------------------------------------------------------------------------

describe("NewsletterContent — unauthenticated", () => {
  beforeEach(() => {
    mockUnauthenticated();
  });

  it("test_newslettercontent_unauth_render_shows_newsletter_title", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.getByRole("heading", { name: mockNewsletter.title })).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_shows_newsletter_subtitle", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.subtitle)).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_shows_agent_label", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.agentLabel)).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_shows_edition_number_and_date", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    // Rendered as: "Edicao #99 · 20 Jan 2026"
    expect(screen.getByText(new RegExp(`Edicao #${mockNewsletter.edition}`))).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_shows_dq_badge_when_present", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.getByText(`DQ: ${mockNewsletter.dqScore}`)).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_omits_dq_badge_when_null", () => {
    render(<NewsletterContent newsletter={mockNewsletterNoDq} />);

    expect(screen.queryByText(/DQ:/)).not.toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_shows_agent_persona_name", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    const persona = AGENT_PERSONAS[mockNewsletter.agent];
    expect(screen.getByText(persona.name)).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_shows_agent_persona_role", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    const persona = AGENT_PERSONAS[mockNewsletter.agent];
    expect(screen.getByText(persona.role)).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_shows_back_link_to_newsletter_archive", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    // "Voltar ao Arquivo" is always rendered at the top of the article
    const backLink = screen.getByText(/Voltar ao Arquivo/);
    expect(backLink.closest("a")).toHaveAttribute("href", "/newsletter");
  });

  it("test_newslettercontent_unauth_render_shows_only_preview_paragraphs", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    // 10 paragraphs → previewCount = Math.ceil(10 * 0.3) = 3
    expect(screen.getByText("Paragraph one content.")).toBeInTheDocument();
    expect(screen.getByText("Paragraph two content.")).toBeInTheDocument();
    expect(screen.getByText("Paragraph three content.")).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_does_not_show_gated_paragraphs", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    // Paragraphs 4–10 are behind the gate and must not be in the DOM
    expect(screen.queryByText("Paragraph four content.")).not.toBeInTheDocument();
    expect(screen.queryByText("Paragraph ten content.")).not.toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_shows_gated_overlay", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    // GatedOverlay's heading is the most reliable sentinel for its presence
    expect(screen.getByRole("heading", { name: "Continue lendo" })).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_does_not_show_footer_note", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    // Footer note is only shown when authenticated or all content fits in preview.
    // The paragraph mixes <strong> and text nodes, so we use the textContent helper.
    expect(queryFooterNote()).not.toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_does_not_show_metodologia_link", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.queryByRole("link", { name: "Metodologia" })).not.toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_does_not_show_fontes_link", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.queryByRole("link", { name: "Fontes" })).not.toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_render_shows_bottom_ver_todas_link", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    // Unauthenticated users with remaining gated paragraphs still get the bottom link
    const bottomLinks = screen.getAllByText(/Ver todas as edicoes/);
    expect(bottomLinks.length).toBeGreaterThanOrEqual(1);
    expect(bottomLinks[0].closest("a")).toHaveAttribute("href", "/newsletter");
  });

  it("test_newslettercontent_unauth_short_body_shows_footer_note_when_no_remaining", () => {
    // When all content fits in the preview (remainingParagraphs.length === 0),
    // the footer note IS shown even for unauthenticated users.
    render(<NewsletterContent newsletter={mockNewsletterShortBody} />);

    expect(queryFooterNote()).toBeInTheDocument();
  });

  it("test_newslettercontent_unauth_short_body_does_not_show_gated_overlay", () => {
    // Single-paragraph body: all content is preview, no gate needed
    render(<NewsletterContent newsletter={mockNewsletterShortBody} />);

    expect(screen.queryByRole("heading", { name: "Continue lendo" })).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// NewsletterContent — authenticated
// ---------------------------------------------------------------------------

describe("NewsletterContent — authenticated", () => {
  beforeEach(() => {
    mockAuthenticated();
  });

  it("test_newslettercontent_auth_render_shows_all_paragraphs", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    // All 10 paragraphs must be visible — none locked behind the gate
    for (let i = 1; i <= 10; i++) {
      expect(screen.getByText(`Paragraph ${wordForNumber(i)} content.`)).toBeInTheDocument();
    }
  });

  it("test_newslettercontent_auth_render_does_not_show_gated_overlay", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.queryByRole("heading", { name: "Continue lendo" })).not.toBeInTheDocument();
  });

  it("test_newslettercontent_auth_render_shows_footer_note", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(queryFooterNote()).toBeInTheDocument();
  });

  it("test_newslettercontent_auth_render_shows_metodologia_link", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    const link = screen.getByRole("link", { name: "Metodologia" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/#metodologia");
  });

  it("test_newslettercontent_auth_render_shows_fontes_link", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.getByRole("link", { name: "Fontes" })).toBeInTheDocument();
  });

  it("test_newslettercontent_auth_render_shows_ver_todas_as_edicoes_link", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    const link = screen.getByRole("link", { name: /Ver todas as edicoes/ });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/newsletter");
  });

  it("test_newslettercontent_auth_render_shows_newsletter_title", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.getByRole("heading", { name: mockNewsletter.title })).toBeInTheDocument();
  });

  it("test_newslettercontent_auth_render_shows_agent_label", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.agentLabel)).toBeInTheDocument();
  });

  it("test_newslettercontent_auth_render_shows_agent_persona_name_and_role", () => {
    render(<NewsletterContent newsletter={mockNewsletter} />);

    const persona = AGENT_PERSONAS[mockNewsletter.agent];
    expect(screen.getByText(persona.name)).toBeInTheDocument();
    expect(screen.getByText(persona.role)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// NewsletterContent — edge cases (other agents / paragraph boundary logic)
// ---------------------------------------------------------------------------

describe("NewsletterContent — edge cases", () => {
  beforeEach(() => {
    mockUnauthenticated();
  });

  it("test_newslettercontent_radar_agent_shows_persona_tomas_aguirre", () => {
    const radarNewsletter: Newsletter = {
      ...mockNewsletter,
      agent: "radar",
      agentLabel: "RADAR",
    };
    render(<NewsletterContent newsletter={radarNewsletter} />);

    expect(screen.getByText("Tomas Aguirre")).toBeInTheDocument();
    expect(screen.getByText("Analista de Tendencias")).toBeInTheDocument();
  });

  it("test_newslettercontent_funding_agent_shows_persona_rafael_oliveira", () => {
    const fundingNewsletter: Newsletter = {
      ...mockNewsletter,
      agent: "funding",
      agentLabel: "FUNDING",
    };
    render(<NewsletterContent newsletter={fundingNewsletter} />);

    expect(screen.getByText("Rafael Oliveira")).toBeInTheDocument();
    expect(screen.getByText("Analista de Investimentos")).toBeInTheDocument();
  });

  it("test_newslettercontent_preview_count_rounds_up_correctly", () => {
    // 7 paragraphs → Math.ceil(7 * 0.3) = Math.ceil(2.1) = 3 shown, 4 gated
    const sevenParagraphBody = Array.from({ length: 7 }, (_, i) => `Para ${i + 1}.`).join("\n\n");
    const newsletter: Newsletter = { ...mockNewsletter, body: sevenParagraphBody };
    render(<NewsletterContent newsletter={newsletter} />);

    expect(screen.getByText("Para 1.")).toBeInTheDocument();
    expect(screen.getByText("Para 2.")).toBeInTheDocument();
    expect(screen.getByText("Para 3.")).toBeInTheDocument();
    // Para 4 is gated and must not be visible
    expect(screen.queryByText("Para 4.")).not.toBeInTheDocument();
  });

  it("test_newslettercontent_body_with_extra_blank_lines_filters_empty_paragraphs", () => {
    // Extra "\n\n" separators produce empty strings — filter(p => p.trim().length > 0)
    // must exclude them so they do not count toward paragraph totals.
    // Body produces 2 real paragraphs after filtering; previewCount = Math.ceil(2*0.3) = 1.
    // "Real para A." is in preview; "Real para B." is gated. No crash from empty strings.
    const bodyWithBlanks = "Real para A.\n\n\n\nReal para B.\n\n";
    const newsletter: Newsletter = { ...mockNewsletter, body: bodyWithBlanks };
    render(<NewsletterContent newsletter={newsletter} />);

    // The first paragraph renders in the preview — confirms empty strings were filtered
    // and the component did not crash or miscalculate paragraph count.
    expect(screen.getByText("Real para A.")).toBeInTheDocument();
    // The second paragraph is gated (behind GatedOverlay), so it is not in the DOM.
    expect(screen.queryByText("Real para B.")).not.toBeInTheDocument();
    // GatedOverlay is present, confirming there ARE remaining paragraphs after filtering.
    expect(screen.getByRole("heading", { name: "Continue lendo" })).toBeInTheDocument();
  });

  it("test_newslettercontent_short_body_unauth_does_not_render_criar_conta_link", () => {
    // Single paragraph: no gating needed, so GatedOverlay is not mounted at all
    render(<NewsletterContent newsletter={mockNewsletterShortBody} />);

    expect(screen.queryByRole("link", { name: "Criar conta gratuita" })).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Utility: map 1–10 to English words for readable paragraph label assertions
// ---------------------------------------------------------------------------

function wordForNumber(n: number): string {
  const words: Record<number, string> = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
  };
  return words[n] ?? String(n);
}

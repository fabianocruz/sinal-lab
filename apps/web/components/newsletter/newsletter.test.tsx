import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import * as nextNavigation from "next/navigation";
import { Newsletter, MOCK_NEWSLETTERS } from "@/lib/newsletter";
import type { ContentApiItem } from "@/lib/newsletter";
import { AGENT_PERSONAS } from "@/lib/constants";

import SearchBar from "@/components/newsletter/SearchBar";
import FilterPills from "@/components/newsletter/FilterPills";
import Pagination, { getPageItems } from "@/components/newsletter/Pagination";
import ArchiveCard from "@/components/newsletter/ArchiveCard";
import FeaturedCard from "@/components/newsletter/FeaturedCard";
import NewsletterArchivePage from "@/app/newsletter/page";
import NewsletterSlugPage from "@/app/newsletter/[slug]/page";

// ---------------------------------------------------------------------------
// Mock API module — page components fetch data from backend.
// ---------------------------------------------------------------------------

vi.mock("@/lib/api", () => ({
  fetchNewsletters: vi.fn(),
  fetchNewsletterBySlug: vi.fn(),
  fetchLatestNewsletter: vi.fn(),
}));

import { fetchNewsletters, fetchNewsletterBySlug } from "@/lib/api";

// ---------------------------------------------------------------------------
// Shared test fixtures
// ---------------------------------------------------------------------------

/** A minimal Newsletter object based on MOCK_NEWSLETTERS[0] (sintese, dqScore present). */
const mockNewsletter: Newsletter = MOCK_NEWSLETTERS[0];

/** A newsletter without a dqScore to exercise the optional badge branch. */
const mockNewsletterNoDq: Newsletter = MOCK_NEWSLETTERS[1]; // dqScore: null

/** Convert a Newsletter mock to a ContentApiItem (as returned by the API). */
function newsletterToApiItem(n: Newsletter): ContentApiItem {
  return {
    id: n.slug,
    title: n.title,
    slug: n.slug,
    content_type: "DATA_REPORT",
    summary: n.subtitle,
    agent_name: n.agent,
    confidence_dq: n.dqScore ? parseFloat(n.dqScore.split("/")[0]) : null,
    confidence_ac: null,
    review_status: "published",
    published_at: `${n.dateISO}T06:00:00Z`,
    sources: n.sources.length > 0 ? n.sources : null,
    meta_description: null,
    author_name: null,
    subtitle: n.subtitle,
    body_md: n.body,
    body_html: null,
    metadata_: n.metadata,
  };
}

const MOCK_API_ITEMS: ContentApiItem[] = MOCK_NEWSLETTERS.map(newsletterToApiItem);

// ---------------------------------------------------------------------------
// SearchBar
// ---------------------------------------------------------------------------

describe("SearchBar", () => {
  it("test_searchbar_render_shows_default_placeholder", () => {
    render(<SearchBar />);

    const input = screen.getByRole("searchbox");
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute("placeholder", "Buscar edições...");
  });

  it("test_searchbar_render_accepts_custom_placeholder", () => {
    render(<SearchBar placeholder="Pesquisar..." />);

    const input = screen.getByRole("searchbox");
    expect(input).toHaveAttribute("placeholder", "Pesquisar...");
  });

  it("test_searchbar_render_has_accessible_label", () => {
    render(<SearchBar />);

    // aria-label on the input
    expect(screen.getByLabelText("Buscar edições")).toBeInTheDocument();
  });

  it("test_searchbar_render_includes_search_icon", () => {
    const { container } = render(<SearchBar />);

    // lucide-react renders an <svg> with aria-hidden="true"
    const svg = container.querySelector('svg[aria-hidden="true"]');
    expect(svg).toBeInTheDocument();
  });

  it("test_searchbar_render_input_is_type_search", () => {
    render(<SearchBar />);

    const input = screen.getByRole("searchbox");
    expect(input).toHaveAttribute("type", "search");
  });
});

// ---------------------------------------------------------------------------
// FilterPills
// ---------------------------------------------------------------------------

describe("FilterPills", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("test_filterpills_render_shows_todos_pill", () => {
    render(<FilterPills />);

    expect(screen.getByText("Todos")).toBeInTheDocument();
  });

  it("test_filterpills_render_todos_is_active_by_default", () => {
    render(<FilterPills />);

    const todosButton = screen.getByText("Todos").closest("button");
    expect(todosButton).toHaveAttribute("aria-pressed", "true");
  });

  it("test_filterpills_render_shows_all_five_agent_pills", () => {
    render(<FilterPills />);

    expect(screen.getByText("Síntese")).toBeInTheDocument();
    expect(screen.getByText("Radar")).toBeInTheDocument();
    expect(screen.getByText("Código")).toBeInTheDocument();
    expect(screen.getByText("Funding")).toBeInTheDocument();
    expect(screen.getByText("Mercado")).toBeInTheDocument();
  });

  it("test_filterpills_render_agent_pills_have_colored_dots", () => {
    const { container } = render(<FilterPills />);

    // Each agent pill (not Todos) has a colored dot <span> with an inline backgroundColor
    const dots = container.querySelectorAll('button span[aria-hidden="true"]');
    expect(dots.length).toBe(5);
    dots.forEach((dot) => {
      expect((dot as HTMLElement).style.backgroundColor).not.toBe("");
    });
  });

  it("test_filterpills_click_agent_pill_makes_it_active", () => {
    const pushMock = vi.fn();
    vi.spyOn(nextNavigation, "useRouter").mockReturnValue({
      push: pushMock,
      replace: vi.fn(),
      refresh: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      prefetch: vi.fn(),
    } as ReturnType<typeof nextNavigation.useRouter>);

    render(<FilterPills />);
    fireEvent.click(screen.getByText("Radar").closest("button")!);

    // Component navigates to the filtered URL — active state comes from URL params
    expect(pushMock).toHaveBeenCalledWith("/newsletter?agent=radar");
  });

  it("test_filterpills_click_agent_pill_deactivates_todos", () => {
    // Simulate URL with agent=radar already active
    vi.spyOn(nextNavigation, "useSearchParams").mockReturnValue(
      new URLSearchParams("agent=radar") as unknown as ReturnType<
        typeof nextNavigation.useSearchParams
      >,
    );

    render(<FilterPills />);

    // With agent=radar in URL, Radar is active and Todos is not
    const todosButton = screen.getByText("Todos").closest("button")!;
    const radarButton = screen.getByText("Radar").closest("button")!;
    expect(radarButton).toHaveAttribute("aria-pressed", "true");
    expect(todosButton).toHaveAttribute("aria-pressed", "false");
  });

  it("test_filterpills_click_todos_after_agent_makes_todos_active_again", () => {
    // Simulate URL with agent=radar active
    vi.spyOn(nextNavigation, "useSearchParams").mockReturnValue(
      new URLSearchParams("agent=radar") as unknown as ReturnType<
        typeof nextNavigation.useSearchParams
      >,
    );
    const pushMock = vi.fn();
    vi.spyOn(nextNavigation, "useRouter").mockReturnValue({
      push: pushMock,
      replace: vi.fn(),
      refresh: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      prefetch: vi.fn(),
    } as ReturnType<typeof nextNavigation.useRouter>);

    render(<FilterPills />);

    // Click Todos to remove the agent filter
    fireEvent.click(screen.getByText("Todos").closest("button")!);

    // Should navigate without agent param
    expect(pushMock).toHaveBeenCalledWith("/newsletter?");
  });

  it("test_filterpills_render_group_has_accessible_label", () => {
    render(<FilterPills />);

    expect(screen.getByRole("group", { name: "Filtrar por agente" })).toBeInTheDocument();
  });

  it("test_filterpills_todos_pill_has_no_colored_dot", () => {
    render(<FilterPills />);

    const todosButton = screen.getByText("Todos").closest("button")!;
    // Todos pill must NOT contain a colored dot span
    const dot = todosButton.querySelector('span[aria-hidden="true"]');
    expect(dot).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

describe("Pagination", () => {
  it("test_pagination_render_shows_all_page_numbers", () => {
    render(<Pagination currentPage={1} totalPages={5} />);

    for (let i = 1; i <= 5; i++) {
      expect(screen.getByText(String(i))).toBeInTheDocument();
    }
  });

  it("test_pagination_render_active_page_has_aria_current_page", () => {
    render(<Pagination currentPage={3} totalPages={5} />);

    const activePage = screen.getByText("3");
    expect(activePage).toHaveAttribute("aria-current", "page");
  });

  it("test_pagination_render_inactive_pages_lack_aria_current", () => {
    render(<Pagination currentPage={3} totalPages={5} />);

    const inactivePage = screen.getByText("1");
    expect(inactivePage).not.toHaveAttribute("aria-current");
  });

  it("test_pagination_render_previous_button_disabled_on_page_1", () => {
    render(<Pagination currentPage={1} totalPages={5} />);

    // Disabled state renders as <span aria-disabled="true"> instead of <button>
    const prev = screen.getByLabelText("Página anterior");
    expect(prev).toHaveAttribute("aria-disabled", "true");
  });

  it("test_pagination_render_previous_button_enabled_when_not_on_page_1", () => {
    render(<Pagination currentPage={2} totalPages={5} />);

    // Enabled state renders as <a> (Link)
    const prev = screen.getByRole("link", { name: "Página anterior" });
    expect(prev).not.toHaveAttribute("aria-disabled");
  });

  it("test_pagination_render_next_button_disabled_on_last_page", () => {
    render(<Pagination currentPage={5} totalPages={5} />);

    const next = screen.getByLabelText("Próxima página");
    expect(next).toHaveAttribute("aria-disabled", "true");
  });

  it("test_pagination_render_next_button_enabled_when_not_on_last_page", () => {
    render(<Pagination currentPage={3} totalPages={5} />);

    const next = screen.getByRole("link", { name: "Próxima página" });
    expect(next).not.toHaveAttribute("aria-disabled");
  });

  it("test_pagination_render_nav_has_accessible_label", () => {
    render(<Pagination currentPage={1} totalPages={5} />);

    expect(screen.getByRole("navigation", { name: "Paginação" })).toBeInTheDocument();
  });

  it("test_pagination_render_single_page_both_buttons_disabled", () => {
    render(<Pagination currentPage={1} totalPages={1} />);

    expect(screen.getByLabelText("Página anterior")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByLabelText("Próxima página")).toHaveAttribute("aria-disabled", "true");
  });

  it("test_pagination_truncates_large_page_counts_with_ellipsis", () => {
    render(<Pagination currentPage={40} totalPages={81} />);

    // Should show first, last, and neighborhood of current
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("39")).toBeInTheDocument();
    expect(screen.getByText("40")).toBeInTheDocument();
    expect(screen.getByText("41")).toBeInTheDocument();
    expect(screen.getByText("81")).toBeInTheDocument();

    // Should NOT show far-away pages
    expect(screen.queryByText("10")).not.toBeInTheDocument();
    expect(screen.queryByText("70")).not.toBeInTheDocument();

    // Should have ellipsis elements
    const ellipses = screen.getAllByText("…");
    expect(ellipses.length).toBe(2);
  });

  it("test_pagination_no_truncation_for_7_or_fewer_pages", () => {
    render(<Pagination currentPage={3} totalPages={7} />);

    for (let i = 1; i <= 7; i++) {
      expect(screen.getByText(String(i))).toBeInTheDocument();
    }
    expect(screen.queryByText("…")).not.toBeInTheDocument();
  });

  it("test_pagination_first_page_shows_no_leading_ellipsis", () => {
    render(<Pagination currentPage={1} totalPages={20} />);

    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();

    // Only one ellipsis (trailing)
    const ellipses = screen.getAllByText("…");
    expect(ellipses.length).toBe(1);
  });

  it("test_pagination_last_page_shows_no_trailing_ellipsis", () => {
    render(<Pagination currentPage={20} totalPages={20} />);

    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("19")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();

    // Only one ellipsis (leading)
    const ellipses = screen.getAllByText("…");
    expect(ellipses.length).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// getPageItems (pure function — unit tests)
// ---------------------------------------------------------------------------

describe("getPageItems", () => {
  it("returns all pages for small totals", () => {
    expect(getPageItems(1, 5)).toEqual([1, 2, 3, 4, 5]);
    expect(getPageItems(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7]);
  });

  it("truncates middle pages for large totals", () => {
    const items = getPageItems(40, 81);
    expect(items).toEqual([1, "ellipsis", 39, 40, 41, "ellipsis", 81]);
  });

  it("shows no leading ellipsis when near start", () => {
    const items = getPageItems(1, 20);
    expect(items).toEqual([1, 2, "ellipsis", 20]);
  });

  it("shows no trailing ellipsis when near end", () => {
    const items = getPageItems(20, 20);
    expect(items).toEqual([1, "ellipsis", 19, 20]);
  });

  it("merges adjacent pages without ellipsis", () => {
    // Page 2: neighborhood is [1, 2, 3], plus first=1 and last=10
    const items = getPageItems(2, 10);
    expect(items).toEqual([1, 2, 3, "ellipsis", 10]);
  });

  it("handles page adjacent to last", () => {
    const items = getPageItems(9, 10);
    expect(items).toEqual([1, "ellipsis", 8, 9, 10]);
  });
});

// ---------------------------------------------------------------------------
// ArchiveCard
// ---------------------------------------------------------------------------

describe("ArchiveCard", () => {
  it("test_archivecard_render_shows_newsletter_title", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.title)).toBeInTheDocument();
  });

  it("test_archivecard_render_shows_newsletter_subtitle", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.subtitle)).toBeInTheDocument();
  });

  it("test_archivecard_render_shows_agent_badge", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.agentLabel)).toBeInTheDocument();
  });

  it("test_archivecard_render_links_to_newsletter_slug", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    const link = screen.getByRole("link", { name: `Ler: ${mockNewsletter.title}` });
    expect(link).toHaveAttribute("href", `/newsletter/${mockNewsletter.slug}`);
  });

  it("test_archivecard_render_shows_dq_score_when_present", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    // mockNewsletter.dqScore is '5/5'
    expect(screen.getByText(`DQ: ${mockNewsletter.dqScore}`)).toBeInTheDocument();
  });

  it("test_archivecard_render_omits_dq_badge_when_null", () => {
    render(<ArchiveCard newsletter={mockNewsletterNoDq} />);

    expect(screen.queryByText(/DQ:/)).not.toBeInTheDocument();
  });

  it("test_archivecard_render_shows_date", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.date)).toBeInTheDocument();
  });

  it("test_archivecard_render_shows_like_count", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    expect(screen.getByText(String(mockNewsletter.likes))).toBeInTheDocument();
  });

  it("test_archivecard_render_shows_persona_name_in_footer", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    const persona = AGENT_PERSONAS[mockNewsletter.agent];
    expect(screen.getByText(persona.name)).toBeInTheDocument();
  });

  it("test_archivecard_render_shows_persona_role_in_footer", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    const persona = AGENT_PERSONAS[mockNewsletter.agent];
    expect(screen.getByText(persona.role)).toBeInTheDocument();
  });

  it("test_archivecard_render_shows_different_persona_for_radar_agent", () => {
    render(<ArchiveCard newsletter={mockNewsletterNoDq} />);

    // mockNewsletterNoDq has agent: "radar"
    expect(screen.getByText("Tomás Aguirre")).toBeInTheDocument();
    expect(screen.getByText("Analista de Tendências")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// FeaturedCard
// ---------------------------------------------------------------------------

describe("FeaturedCard", () => {
  it("test_featuredcard_render_shows_newsletter_title", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.title)).toBeInTheDocument();
  });

  it("test_featuredcard_render_shows_newsletter_subtitle", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.subtitle)).toBeInTheDocument();
  });

  it("test_featuredcard_render_shows_agent_badge", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    expect(screen.getByText(mockNewsletter.agentLabel)).toBeInTheDocument();
  });

  it("test_featuredcard_render_links_to_newsletter_slug", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    const link = screen.getByRole("link", {
      name: `Ler edição em destaque: ${mockNewsletter.title}`,
    });
    expect(link).toHaveAttribute("href", `/newsletter/${mockNewsletter.slug}`);
  });

  it("test_featuredcard_render_has_two_column_grid_class", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    const link = screen.getByRole("link", {
      name: `Ler edição em destaque: ${mockNewsletter.title}`,
    });
    // The md:grid-cols-[1.2fr_1fr] class signals the 2-column layout
    expect(link.className).toContain("grid-cols");
  });

  it("test_featuredcard_render_shows_dq_score_when_present", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    expect(screen.getByText(`DQ: ${mockNewsletter.dqScore}`)).toBeInTheDocument();
  });

  it("test_featuredcard_render_omits_dq_badge_when_null", () => {
    render(<FeaturedCard newsletter={mockNewsletterNoDq} />);

    expect(screen.queryByText(/DQ:/)).not.toBeInTheDocument();
  });

  it("test_featuredcard_render_shows_edition_number", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    expect(screen.getByText(new RegExp(`Ed. #${mockNewsletter.edition}`))).toBeInTheDocument();
  });

  it("test_featuredcard_render_shows_persona_name_in_footer", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    const persona = AGENT_PERSONAS[mockNewsletter.agent];
    expect(screen.getByText(persona.name)).toBeInTheDocument();
  });

  it("test_featuredcard_render_shows_persona_role_in_footer", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    const persona = AGENT_PERSONAS[mockNewsletter.agent];
    expect(screen.getByText(persona.role)).toBeInTheDocument();
  });

  it("test_featuredcard_render_shows_different_persona_for_radar_agent", () => {
    render(<FeaturedCard newsletter={mockNewsletterNoDq} />);

    // mockNewsletterNoDq has agent: "radar"
    expect(screen.getByText("Tomás Aguirre")).toBeInTheDocument();
    expect(screen.getByText("Analista de Tendências")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Archive page (app/newsletter/page.tsx) — async Server Component
// ---------------------------------------------------------------------------

describe("NewsletterArchivePage", () => {
  beforeEach(() => {
    vi.mocked(fetchNewsletters).mockResolvedValue({
      items: MOCK_API_ITEMS,
      total: MOCK_API_ITEMS.length,
      limit: 7,
      offset: 0,
    });
  });

  it("test_archivepage_render_shows_arquivo_heading", async () => {
    const jsx = await NewsletterArchivePage({ searchParams: {} });
    render(jsx);

    expect(screen.getByRole("heading", { name: "Arquivo" })).toBeInTheDocument();
  });

  it("test_archivepage_render_has_search_bar", async () => {
    const jsx = await NewsletterArchivePage({ searchParams: {} });
    render(jsx);

    expect(screen.getByRole("searchbox")).toBeInTheDocument();
  });

  it("test_archivepage_render_has_filter_pills", async () => {
    const jsx = await NewsletterArchivePage({ searchParams: {} });
    render(jsx);

    expect(screen.getByRole("group", { name: "Filtrar por agente" })).toBeInTheDocument();
  });

  it("test_archivepage_render_shows_featured_card_for_first_newsletter", async () => {
    const jsx = await NewsletterArchivePage({ searchParams: {} });
    render(jsx);

    const featured = MOCK_NEWSLETTERS[0];
    // FeaturedCard uses "Ler edição em destaque: …" as its aria-label
    expect(
      screen.getByRole("link", { name: `Ler edição em destaque: ${featured.title}` }),
    ).toBeInTheDocument();
  });

  it("test_archivepage_render_shows_archive_cards_for_remaining_newsletters", async () => {
    const jsx = await NewsletterArchivePage({ searchParams: {} });
    render(jsx);

    // All newsletters after the first are rendered as ArchiveCards
    const rest = MOCK_NEWSLETTERS.slice(1);
    rest.forEach((n) => {
      expect(screen.getByRole("link", { name: `Ler: ${n.title}` })).toBeInTheDocument();
    });
  });

  it("test_archivepage_render_featured_newsletter_not_duplicated_as_archive_card", async () => {
    const jsx = await NewsletterArchivePage({ searchParams: {} });
    render(jsx);

    const featured = MOCK_NEWSLETTERS[0];
    // The first newsletter should appear only once as a FeaturedCard, not also as an ArchiveCard
    expect(screen.queryByRole("link", { name: `Ler: ${featured.title}` })).not.toBeInTheDocument();
  });

  it("test_archivepage_render_shows_pagination", async () => {
    const jsx = await NewsletterArchivePage({ searchParams: {} });
    render(jsx);

    expect(screen.getByRole("navigation", { name: "Paginação" })).toBeInTheDocument();
  });

  it("test_archivepage_render_pagination_starts_on_page_1", async () => {
    const jsx = await NewsletterArchivePage({ searchParams: {} });
    render(jsx);

    // Disabled previous button renders as <span aria-disabled="true">
    expect(screen.getByLabelText("Página anterior")).toHaveAttribute("aria-disabled", "true");
  });
});

// ---------------------------------------------------------------------------
// Newsletter slug page (app/newsletter/[slug]/page.tsx) — async Server Component
// ---------------------------------------------------------------------------

describe("NewsletterSlugPage", () => {
  const validSlug = "briefing-47-paradoxo-modelo-gratuito";
  const validNewsletter = MOCK_NEWSLETTERS.find((n) => n.slug === validSlug)!;

  beforeEach(() => {
    vi.mocked(fetchNewsletterBySlug).mockImplementation(async (slug: string) => {
      const item = MOCK_API_ITEMS.find((i) => i.slug === slug);
      return item ?? null;
    });
  });

  it("test_slugpage_render_shows_newsletter_title_for_valid_slug", async () => {
    const jsx = await NewsletterSlugPage({ params: { slug: validSlug } });
    render(jsx);

    expect(screen.getByRole("heading", { name: validNewsletter.title })).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_agent_badge", async () => {
    const jsx = await NewsletterSlugPage({ params: { slug: validSlug } });
    render(jsx);

    // agentLabel appears in the article header meta row
    expect(screen.getByText(validNewsletter.agentLabel)).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_article_body_content", async () => {
    const jsx = await NewsletterSlugPage({ params: { slug: validSlug } });
    render(jsx);

    // The body is split on "\n\n" — test that the first paragraph is present
    const firstParagraph = validNewsletter.body.split("\n\n")[0].trim();
    expect(screen.getByText(firstParagraph)).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_subtitle", async () => {
    const jsx = await NewsletterSlugPage({ params: { slug: validSlug } });
    render(jsx);

    expect(screen.getByText(validNewsletter.subtitle)).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_edition_number", async () => {
    const jsx = await NewsletterSlugPage({ params: { slug: validSlug } });
    render(jsx);

    expect(screen.getByText(new RegExp(`Edição #${validNewsletter.edition}`))).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_dq_score_when_present", async () => {
    const jsx = await NewsletterSlugPage({ params: { slug: validSlug } });
    render(jsx);

    expect(screen.getByText(`DQ: ${validNewsletter.dqScore}`)).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_agent_persona_name", async () => {
    const jsx = await NewsletterSlugPage({ params: { slug: validSlug } });
    render(jsx);

    // AGENT_PERSONAS.sintese.name = 'Clara Medeiros'
    expect(screen.getByText("Clara Medeiros")).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_back_link_to_archive", async () => {
    const jsx = await NewsletterSlugPage({ params: { slug: validSlug } });
    render(jsx);

    const backLinks = screen.getAllByRole("link", { name: /Voltar ao Arquivo/i });
    expect(backLinks.length).toBeGreaterThanOrEqual(1);
    expect(backLinks[0]).toHaveAttribute("href", "/newsletter");
  });

  it("test_slugpage_render_calls_notfound_for_unknown_slug", async () => {
    // next/navigation.notFound is mocked as vi.fn() in test/setup.tsx — it does NOT
    // throw, so execution falls through and the component crashes accessing undefined.
    // We verify that notFound was called, and suppress the downstream TypeError.
    const notFoundMock = vi.mocked(nextNavigation.notFound);
    notFoundMock.mockClear();

    try {
      const jsx = await NewsletterSlugPage({ params: { slug: "slug-que-nao-existe" } });
      render(jsx);
    } catch {
      // Expected: component crashes after the no-op notFound() mock
    }

    expect(notFoundMock).toHaveBeenCalled();
  });

  it("test_slugpage_render_newsletter_with_null_dq_score_omits_dq_badge", async () => {
    const noDqSlug = "briefing-46-healthtech-latam"; // dqScore: null
    const jsx = await NewsletterSlugPage({ params: { slug: noDqSlug } });
    render(jsx);

    expect(screen.queryByText(/DQ:/)).not.toBeInTheDocument();
  });
});

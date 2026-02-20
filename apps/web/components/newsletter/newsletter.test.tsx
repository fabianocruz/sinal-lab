import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import * as nextNavigation from "next/navigation";
import { Newsletter, MOCK_NEWSLETTERS } from "@/lib/newsletter";

import SearchBar from "@/components/newsletter/SearchBar";
import FilterPills from "@/components/newsletter/FilterPills";
import Pagination from "@/components/newsletter/Pagination";
import ArchiveCard from "@/components/newsletter/ArchiveCard";
import FeaturedCard from "@/components/newsletter/FeaturedCard";
import NewsletterArchivePage from "@/app/newsletter/page";
import NewsletterSlugPage from "@/app/newsletter/[slug]/page";

// ---------------------------------------------------------------------------
// Shared test fixtures
// ---------------------------------------------------------------------------

/** A minimal Newsletter object based on MOCK_NEWSLETTERS[0] (sintese, dqScore present). */
const mockNewsletter: Newsletter = MOCK_NEWSLETTERS[0];

/** A newsletter without a dqScore to exercise the optional badge branch. */
const mockNewsletterNoDq: Newsletter = MOCK_NEWSLETTERS[1]; // dqScore: null

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
    render(<FilterPills />);

    const radarButton = screen.getByText("Radar").closest("button")!;
    fireEvent.click(radarButton);

    expect(radarButton).toHaveAttribute("aria-pressed", "true");
  });

  it("test_filterpills_click_agent_pill_deactivates_todos", () => {
    render(<FilterPills />);

    const todosButton = screen.getByText("Todos").closest("button")!;
    const radarButton = screen.getByText("Radar").closest("button")!;

    fireEvent.click(radarButton);

    expect(todosButton).toHaveAttribute("aria-pressed", "false");
  });

  it("test_filterpills_click_todos_after_agent_makes_todos_active_again", () => {
    render(<FilterPills />);

    const todosButton = screen.getByText("Todos").closest("button")!;
    const radarButton = screen.getByText("Radar").closest("button")!;

    fireEvent.click(radarButton);
    fireEvent.click(todosButton);

    expect(todosButton).toHaveAttribute("aria-pressed", "true");
    expect(radarButton).toHaveAttribute("aria-pressed", "false");
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

    const prev = screen.getByRole("button", { name: "Página anterior" });
    expect(prev).toBeDisabled();
  });

  it("test_pagination_render_previous_button_enabled_when_not_on_page_1", () => {
    render(<Pagination currentPage={2} totalPages={5} />);

    const prev = screen.getByRole("button", { name: "Página anterior" });
    expect(prev).not.toBeDisabled();
  });

  it("test_pagination_render_next_button_disabled_on_last_page", () => {
    render(<Pagination currentPage={5} totalPages={5} />);

    const next = screen.getByRole("button", { name: "Próxima página" });
    expect(next).toBeDisabled();
  });

  it("test_pagination_render_next_button_enabled_when_not_on_last_page", () => {
    render(<Pagination currentPage={3} totalPages={5} />);

    const next = screen.getByRole("button", { name: "Próxima página" });
    expect(next).not.toBeDisabled();
  });

  it("test_pagination_render_nav_has_accessible_label", () => {
    render(<Pagination currentPage={1} totalPages={5} />);

    expect(screen.getByRole("navigation", { name: "Paginação" })).toBeInTheDocument();
  });

  it("test_pagination_render_single_page_both_buttons_disabled", () => {
    render(<Pagination currentPage={1} totalPages={1} />);

    expect(screen.getByRole("button", { name: "Página anterior" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Próxima página" })).toBeDisabled();
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

  it("test_archivecard_render_shows_agent_label_in_footer", () => {
    render(<ArchiveCard newsletter={mockNewsletter} />);

    // Footer text: "Agente SINTESE"
    expect(screen.getByText(`Agente ${mockNewsletter.agentLabel}`)).toBeInTheDocument();
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

  it("test_featuredcard_render_shows_agent_label_in_footer", () => {
    render(<FeaturedCard newsletter={mockNewsletter} />);

    expect(screen.getByText(`Agente ${mockNewsletter.agentLabel}`)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Archive page (app/newsletter/page.tsx)
// ---------------------------------------------------------------------------

describe("NewsletterArchivePage", () => {
  it("test_archivepage_render_shows_arquivo_heading", () => {
    render(<NewsletterArchivePage />);

    expect(screen.getByRole("heading", { name: "Arquivo" })).toBeInTheDocument();
  });

  it("test_archivepage_render_has_search_bar", () => {
    render(<NewsletterArchivePage />);

    expect(screen.getByRole("searchbox")).toBeInTheDocument();
  });

  it("test_archivepage_render_has_filter_pills", () => {
    render(<NewsletterArchivePage />);

    expect(screen.getByRole("group", { name: "Filtrar por agente" })).toBeInTheDocument();
  });

  it("test_archivepage_render_shows_featured_card_for_first_newsletter", () => {
    render(<NewsletterArchivePage />);

    const featured = MOCK_NEWSLETTERS[0];
    // FeaturedCard uses "Ler edição em destaque: …" as its aria-label
    expect(
      screen.getByRole("link", { name: `Ler edição em destaque: ${featured.title}` }),
    ).toBeInTheDocument();
  });

  it("test_archivepage_render_shows_archive_cards_for_remaining_newsletters", () => {
    render(<NewsletterArchivePage />);

    // All newsletters after the first are rendered as ArchiveCards
    const rest = MOCK_NEWSLETTERS.slice(1);
    rest.forEach((n) => {
      expect(screen.getByRole("link", { name: `Ler: ${n.title}` })).toBeInTheDocument();
    });
  });

  it("test_archivepage_render_featured_newsletter_not_duplicated_as_archive_card", () => {
    render(<NewsletterArchivePage />);

    const featured = MOCK_NEWSLETTERS[0];
    // The first newsletter should appear only once as a FeaturedCard, not also as an ArchiveCard
    expect(screen.queryByRole("link", { name: `Ler: ${featured.title}` })).not.toBeInTheDocument();
  });

  it("test_archivepage_render_shows_pagination", () => {
    render(<NewsletterArchivePage />);

    expect(screen.getByRole("navigation", { name: "Paginação" })).toBeInTheDocument();
  });

  it("test_archivepage_render_pagination_starts_on_page_1", () => {
    render(<NewsletterArchivePage />);

    expect(screen.getByRole("button", { name: "Página anterior" })).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// Newsletter slug page (app/newsletter/[slug]/page.tsx)
// ---------------------------------------------------------------------------

describe("NewsletterSlugPage", () => {
  const validSlug = "briefing-47-paradoxo-modelo-gratuito";
  const validNewsletter = MOCK_NEWSLETTERS.find((n) => n.slug === validSlug)!;

  it("test_slugpage_render_shows_newsletter_title_for_valid_slug", () => {
    render(<NewsletterSlugPage params={{ slug: validSlug }} />);

    expect(screen.getByRole("heading", { name: validNewsletter.title })).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_agent_badge", () => {
    render(<NewsletterSlugPage params={{ slug: validSlug }} />);

    // agentLabel appears in the article header meta row
    expect(screen.getByText(validNewsletter.agentLabel)).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_article_body_content", () => {
    render(<NewsletterSlugPage params={{ slug: validSlug }} />);

    // The body is split on "\n\n" — test that the first paragraph is present
    const firstParagraph = validNewsletter.body.split("\n\n")[0].trim();
    expect(screen.getByText(firstParagraph)).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_subtitle", () => {
    render(<NewsletterSlugPage params={{ slug: validSlug }} />);

    expect(screen.getByText(validNewsletter.subtitle)).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_edition_number", () => {
    render(<NewsletterSlugPage params={{ slug: validSlug }} />);

    expect(screen.getByText(new RegExp(`Edição #${validNewsletter.edition}`))).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_dq_score_when_present", () => {
    render(<NewsletterSlugPage params={{ slug: validSlug }} />);

    expect(screen.getByText(`DQ: ${validNewsletter.dqScore}`)).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_agent_persona_name", () => {
    render(<NewsletterSlugPage params={{ slug: validSlug }} />);

    // AGENT_PERSONAS.sintese.name = 'Clara Medeiros'
    expect(screen.getByText("Clara Medeiros")).toBeInTheDocument();
  });

  it("test_slugpage_render_shows_back_link_to_archive", () => {
    render(<NewsletterSlugPage params={{ slug: validSlug }} />);

    const backLinks = screen.getAllByRole("link", { name: /Voltar ao Arquivo/i });
    expect(backLinks.length).toBeGreaterThanOrEqual(1);
    expect(backLinks[0]).toHaveAttribute("href", "/newsletter");
  });

  it("test_slugpage_render_calls_notfound_for_unknown_slug", () => {
    // next/navigation.notFound is mocked as vi.fn() in test/setup.tsx — it does NOT
    // throw, so execution falls through and the component crashes accessing undefined.
    // We verify that notFound was called, and suppress the downstream TypeError.
    const notFoundMock = vi.mocked(nextNavigation.notFound);
    notFoundMock.mockClear();

    try {
      render(<NewsletterSlugPage params={{ slug: "slug-que-nao-existe" }} />);
    } catch {
      // Expected: component crashes after the no-op notFound() mock
    }

    expect(notFoundMock).toHaveBeenCalled();
  });

  it("test_slugpage_render_newsletter_with_null_dq_score_omits_dq_badge", () => {
    const noDqSlug = "briefing-46-healthtech-latam"; // dqScore: null
    render(<NewsletterSlugPage params={{ slug: noDqSlug }} />);

    expect(screen.queryByText(/DQ:/)).not.toBeInTheDocument();
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import NewsletterArchiveError from "@/app/newsletter/error";
import NewsletterArchiveLoading from "@/app/newsletter/loading";
import NewsletterSlugError from "@/app/newsletter/[slug]/error";
import NewsletterSlugLoading from "@/app/newsletter/[slug]/loading";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeError(message = "Test error"): Error {
  return new Error(message);
}

// ---------------------------------------------------------------------------
// NewsletterArchiveError
// ---------------------------------------------------------------------------

describe("NewsletterArchiveError", () => {
  it("test_archive_error_renders_erro_label", () => {
    render(<NewsletterArchiveError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByText("Erro")).toBeInTheDocument();
  });

  it("test_archive_error_renders_algo_deu_errado_heading", () => {
    render(<NewsletterArchiveError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Algo deu errado" })).toBeInTheDocument();
  });

  it("test_archive_error_renders_archive_description_text", () => {
    render(<NewsletterArchiveError error={makeError()} reset={vi.fn()} />);

    expect(
      screen.getByText("Não foi possível carregar o arquivo de edições. Tente novamente."),
    ).toBeInTheDocument();
  });

  it("test_archive_error_renders_tentar_novamente_button", () => {
    render(<NewsletterArchiveError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("test_archive_error_clicking_tentar_novamente_calls_reset", () => {
    const reset = vi.fn();
    render(<NewsletterArchiveError error={makeError()} reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("test_archive_error_reset_not_called_on_initial_render", () => {
    const reset = vi.fn();
    render(<NewsletterArchiveError error={makeError()} reset={reset} />);

    expect(reset).not.toHaveBeenCalled();
  });

  it("test_archive_error_renders_voltar_ao_inicio_link", () => {
    render(<NewsletterArchiveError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByRole("link", { name: "Voltar ao início" })).toBeInTheDocument();
  });

  it("test_archive_error_voltar_ao_inicio_link_points_to_root", () => {
    render(<NewsletterArchiveError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByRole("link", { name: "Voltar ao início" })).toHaveAttribute("href", "/");
  });

  it("test_archive_error_has_min_h_screen_centering_wrapper", () => {
    const { container } = render(<NewsletterArchiveError error={makeError()} reset={vi.fn()} />);

    const outer = container.firstElementChild as HTMLElement;
    expect(outer.className).toContain("min-h-screen");
    expect(outer.className).toContain("items-center");
  });

  it("test_archive_error_has_pt_72px_navbar_offset", () => {
    const { container } = render(<NewsletterArchiveError error={makeError()} reset={vi.fn()} />);

    const outer = container.firstElementChild as HTMLElement;
    expect(outer.className).toContain("pt-[72px]");
  });
});

// ---------------------------------------------------------------------------
// NewsletterArchiveLoading
// ---------------------------------------------------------------------------

describe("NewsletterArchiveLoading", () => {
  it("test_archive_loading_renders_without_crashing", () => {
    expect(() => render(<NewsletterArchiveLoading />)).not.toThrow();
  });

  it("test_archive_loading_has_pt_72px_navbar_offset", () => {
    const { container } = render(<NewsletterArchiveLoading />);

    const outer = container.firstElementChild as HTMLElement;
    expect(outer.className).toContain("pt-[72px]");
  });

  it("test_archive_loading_contains_multiple_animate_pulse_elements", () => {
    const { container } = render(<NewsletterArchiveLoading />);

    const pulsingElements = container.querySelectorAll(".animate-pulse");
    expect(pulsingElements.length).toBeGreaterThan(5);
  });

  it("test_archive_loading_renders_six_filter_pill_skeletons", () => {
    const { container } = render(<NewsletterArchiveLoading />);

    // Filter pills: h-9 w-20 animate-pulse rounded-lg bg-sinal-graphite
    const pillSkeletons = container.querySelectorAll(".h-9.w-20.animate-pulse");
    expect(pillSkeletons).toHaveLength(6);
  });

  it("test_archive_loading_renders_featured_card_skeleton_with_col_span_full", () => {
    const { container } = render(<NewsletterArchiveLoading />);

    const featuredSkeleton = container.querySelector(".col-span-full");
    expect(featuredSkeleton).toBeInTheDocument();
    expect((featuredSkeleton as HTMLElement).className).toContain("animate-pulse");
  });

  it("test_archive_loading_renders_six_regular_card_skeletons", () => {
    const { container } = render(<NewsletterArchiveLoading />);

    // Regular card skeletons: h-[360px] animate-pulse rounded-2xl
    const cardSkeletons = container.querySelectorAll(".h-\\[360px\\].animate-pulse");
    expect(cardSkeletons).toHaveLength(6);
  });

  it("test_archive_loading_header_skeleton_contains_title_and_subtitle_bones", () => {
    const { container } = render(<NewsletterArchiveLoading />);

    // The header block has h-10 (title) and h-4 (subtitle) skeletons
    const titleBone = container.querySelector(".h-10.w-48.animate-pulse");
    const subtitleBone = container.querySelector(".h-4.w-72.animate-pulse");

    expect(titleBone).toBeInTheDocument();
    expect(subtitleBone).toBeInTheDocument();
  });

  it("test_archive_loading_header_skeleton_contains_search_bone", () => {
    const { container } = render(<NewsletterArchiveLoading />);

    // Search bar skeleton: h-12 w-[280px]
    const searchBone = container.querySelector(".h-12.w-\\[280px\\].animate-pulse");
    expect(searchBone).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// NewsletterSlugError
// ---------------------------------------------------------------------------

describe("NewsletterSlugError", () => {
  it("test_slug_error_renders_edicao_nao_encontrada_label", () => {
    render(<NewsletterSlugError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByText("Edição não encontrada")).toBeInTheDocument();
  });

  it("test_slug_error_renders_algo_deu_errado_heading", () => {
    render(<NewsletterSlugError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Algo deu errado" })).toBeInTheDocument();
  });

  it("test_slug_error_renders_edition_description_text", () => {
    render(<NewsletterSlugError error={makeError()} reset={vi.fn()} />);

    expect(
      screen.getByText(
        "Não foi possível carregar esta edição. Ela pode ter sido movida ou removida.",
      ),
    ).toBeInTheDocument();
  });

  it("test_slug_error_renders_tentar_novamente_button", () => {
    render(<NewsletterSlugError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("test_slug_error_clicking_tentar_novamente_calls_reset", () => {
    const reset = vi.fn();
    render(<NewsletterSlugError error={makeError()} reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("test_slug_error_reset_not_called_on_initial_render", () => {
    const reset = vi.fn();
    render(<NewsletterSlugError error={makeError()} reset={reset} />);

    expect(reset).not.toHaveBeenCalled();
  });

  it("test_slug_error_renders_ver_todas_as_edicoes_link", () => {
    render(<NewsletterSlugError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByRole("link", { name: "Ver todas as edições" })).toBeInTheDocument();
  });

  it("test_slug_error_ver_todas_link_points_to_newsletter_archive", () => {
    render(<NewsletterSlugError error={makeError()} reset={vi.fn()} />);

    expect(screen.getByRole("link", { name: "Ver todas as edições" })).toHaveAttribute(
      "href",
      "/newsletter",
    );
  });

  it("test_slug_error_has_min_h_screen_centering_wrapper", () => {
    const { container } = render(<NewsletterSlugError error={makeError()} reset={vi.fn()} />);

    const outer = container.firstElementChild as HTMLElement;
    expect(outer.className).toContain("min-h-screen");
    expect(outer.className).toContain("items-center");
  });

  it("test_slug_error_has_pt_72px_navbar_offset", () => {
    const { container } = render(<NewsletterSlugError error={makeError()} reset={vi.fn()} />);

    const outer = container.firstElementChild as HTMLElement;
    expect(outer.className).toContain("pt-[72px]");
  });

  it("test_slug_error_label_differs_from_archive_error_label", () => {
    // Guard: the two error pages must have distinct labels so users know
    // which context failed.
    render(<NewsletterSlugError error={makeError()} reset={vi.fn()} />);

    expect(screen.queryByText("Erro")).not.toBeInTheDocument();
    expect(screen.getByText("Edição não encontrada")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// NewsletterSlugLoading
// ---------------------------------------------------------------------------

describe("NewsletterSlugLoading", () => {
  it("test_slug_loading_renders_without_crashing", () => {
    expect(() => render(<NewsletterSlugLoading />)).not.toThrow();
  });

  it("test_slug_loading_has_pt_72px_navbar_offset", () => {
    const { container } = render(<NewsletterSlugLoading />);

    const outer = container.firstElementChild as HTMLElement;
    expect(outer.className).toContain("pt-[72px]");
  });

  it("test_slug_loading_contains_multiple_animate_pulse_elements", () => {
    const { container } = render(<NewsletterSlugLoading />);

    const pulsingElements = container.querySelectorAll(".animate-pulse");
    expect(pulsingElements.length).toBeGreaterThan(5);
  });

  it("test_slug_loading_renders_back_link_skeleton", () => {
    const { container } = render(<NewsletterSlugLoading />);

    // Back link skeleton: mb-8 h-4 w-32
    const backLinkBone = container.querySelector(".mb-8.h-4.w-32.animate-pulse");
    expect(backLinkBone).toBeInTheDocument();
  });

  it("test_slug_loading_renders_avatar_with_rounded_full_class", () => {
    const { container } = render(<NewsletterSlugLoading />);

    const avatarBone = container.querySelector(".rounded-full.animate-pulse");
    expect(avatarBone).toBeInTheDocument();
  });

  it("test_slug_loading_avatar_is_square_8x8", () => {
    const { container } = render(<NewsletterSlugLoading />);

    // Avatar: h-8 w-8 rounded-full animate-pulse
    const avatarBone = container.querySelector(".h-8.w-8.rounded-full.animate-pulse");
    expect(avatarBone).toBeInTheDocument();
  });

  it("test_slug_loading_renders_five_body_line_skeletons", () => {
    const { container } = render(<NewsletterSlugLoading />);

    // Body lines live inside the .space-y-4 wrapper — the header also has an
    // h-5 skeleton (the subtitle bone, w-2/3) so we must scope to the body div.
    const bodyLines = container.querySelectorAll(".space-y-4 .h-5.animate-pulse");
    expect(bodyLines).toHaveLength(5);
  });

  it("test_slug_loading_body_lines_have_inline_width_styles", () => {
    const { container } = render(<NewsletterSlugLoading />);

    // Each body line has a style.width set to a percentage value.
    // Scope to .space-y-4 to exclude the header h-5 (w-2/3 Tailwind class, no inline style).
    const bodyLines = container.querySelectorAll(".space-y-4 .h-5.animate-pulse");
    bodyLines.forEach((line) => {
      expect((line as HTMLElement).style.width).toMatch(/^\d+%$/);
    });
  });

  it("test_slug_loading_renders_header_section_inside_article", () => {
    const { container } = render(<NewsletterSlugLoading />);

    const article = container.querySelector("article");
    expect(article).toBeInTheDocument();

    const header = article!.querySelector("header");
    expect(header).toBeInTheDocument();
  });

  it("test_slug_loading_header_skeleton_contains_agent_and_date_bones", () => {
    const { container } = render(<NewsletterSlugLoading />);

    // Agent pill: h-4 w-20; date: h-4 w-32 — both inside the flex gap-3 row
    const agentBone = container.querySelector(".h-4.w-20.animate-pulse");
    const dateBone = container.querySelector(".h-4.w-32.animate-pulse");

    expect(agentBone).toBeInTheDocument();
    expect(dateBone).toBeInTheDocument();
  });
});

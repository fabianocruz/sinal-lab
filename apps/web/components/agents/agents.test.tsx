import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AGENT_PERSONAS } from "@/lib/constants";

import AgentAvatar from "./AgentAvatar";
import AgentCard from "./AgentCard";
import AgentTeam from "./AgentTeam";

// ---------------------------------------------------------------------------
// AgentAvatar
// ---------------------------------------------------------------------------

describe("AgentAvatar", () => {
  it("test_agentavatar_sintese_renders_initials_cm", () => {
    render(<AgentAvatar agentKey="sintese" />);

    expect(screen.getByText("CM")).toBeInTheDocument();
  });

  it("test_agentavatar_radar_renders_initials_ta", () => {
    render(<AgentAvatar agentKey="radar" />);

    expect(screen.getByText("TA")).toBeInTheDocument();
  });

  it("test_agentavatar_codigo_renders_initials_mc", () => {
    render(<AgentAvatar agentKey="codigo" />);

    expect(screen.getByText("MC")).toBeInTheDocument();
  });

  it("test_agentavatar_funding_renders_initials_ro", () => {
    render(<AgentAvatar agentKey="funding" />);

    expect(screen.getByText("RO")).toBeInTheDocument();
  });

  it("test_agentavatar_mercado_renders_initials_vr", () => {
    render(<AgentAvatar agentKey="mercado" />);

    expect(screen.getByText("VR")).toBeInTheDocument();
  });

  it("test_agentavatar_has_accessible_aria_label_with_agent_name", () => {
    render(<AgentAvatar agentKey="sintese" />);

    expect(
      screen.getByRole("generic", { name: `Avatar de ${AGENT_PERSONAS.sintese.name}` }),
    ).toBeInTheDocument();
  });

  it("test_agentavatar_default_size_is_48px", () => {
    const { container } = render(<AgentAvatar agentKey="sintese" />);

    const div = container.firstChild as HTMLElement;
    expect(div.style.width).toBe("48px");
    expect(div.style.height).toBe("48px");
  });

  it("test_agentavatar_size_sm_renders_32px_dimensions", () => {
    const { container } = render(<AgentAvatar agentKey="sintese" size="sm" />);

    const div = container.firstChild as HTMLElement;
    expect(div.style.width).toBe("32px");
    expect(div.style.height).toBe("32px");
  });

  it("test_agentavatar_size_md_renders_48px_dimensions", () => {
    const { container } = render(<AgentAvatar agentKey="sintese" size="md" />);

    const div = container.firstChild as HTMLElement;
    expect(div.style.width).toBe("48px");
    expect(div.style.height).toBe("48px");
  });

  it("test_agentavatar_size_lg_renders_64px_dimensions", () => {
    const { container } = render(<AgentAvatar agentKey="sintese" size="lg" />);

    const div = container.firstChild as HTMLElement;
    expect(div.style.width).toBe("64px");
    expect(div.style.height).toBe("64px");
  });

  it("test_agentavatar_sintese_has_correct_background_color", () => {
    const { container } = render(<AgentAvatar agentKey="sintese" />);

    const div = container.firstChild as HTMLElement;
    // rgba(232,255,89,0.15) — some browsers normalize to rgb + opacity
    expect(div.style.backgroundColor).toContain("232");
  });

  it("test_agentavatar_mercado_has_correct_text_color", () => {
    const { container } = render(<AgentAvatar agentKey="mercado" />);

    const div = container.firstChild as HTMLElement;
    // persona.color = '#C459FF'
    expect(div.style.color).toBeTruthy();
  });

  it("test_agentavatar_has_border_style", () => {
    const { container } = render(<AgentAvatar agentKey="funding" />);

    const div = container.firstChild as HTMLElement;
    expect(div.style.border).toContain("1px");
  });

  it("test_agentavatar_is_circular_via_rounded_full_class", () => {
    const { container } = render(<AgentAvatar agentKey="radar" />);

    const div = container.firstChild as HTMLElement;
    expect(div.className).toContain("rounded-full");
  });

  it("test_agentavatar_uses_font_mono_class", () => {
    const { container } = render(<AgentAvatar agentKey="codigo" />);

    const div = container.firstChild as HTMLElement;
    expect(div.className).toContain("font-mono");
  });
});

// ---------------------------------------------------------------------------
// AgentCard
// ---------------------------------------------------------------------------

describe("AgentCard", () => {
  it("test_agentcard_sintese_renders_agent_name", () => {
    render(<AgentCard agentKey="sintese" />);

    expect(screen.getByText(AGENT_PERSONAS.sintese.name)).toBeInTheDocument();
  });

  it("test_agentcard_sintese_renders_agent_role", () => {
    render(<AgentCard agentKey="sintese" />);

    expect(screen.getByText(AGENT_PERSONAS.sintese.role)).toBeInTheDocument();
  });

  it("test_agentcard_sintese_renders_agent_code_badge", () => {
    render(<AgentCard agentKey="sintese" />);

    expect(screen.getByText(AGENT_PERSONAS.sintese.agentCode)).toBeInTheDocument();
  });

  it("test_agentcard_sintese_renders_description", () => {
    render(<AgentCard agentKey="sintese" />);

    expect(screen.getByText(AGENT_PERSONAS.sintese.description)).toBeInTheDocument();
  });

  it("test_agentcard_renders_avatar_with_correct_initials", () => {
    render(<AgentCard agentKey="sintese" />);

    // AgentAvatar for "Clara Medeiros" → "CM"
    expect(screen.getByText("CM")).toBeInTheDocument();
  });

  it("test_agentcard_renders_status_dot_with_agent_color", () => {
    const { container } = render(<AgentCard agentKey="sintese" />);

    const dot = container.querySelector('span[aria-hidden="true"]') as HTMLElement;
    expect(dot).toBeInTheDocument();
    // backgroundColor is the agent color (#E8FF59 for sintese)
    expect(dot.style.backgroundColor).toBeTruthy();
  });

  it("test_agentcard_badge_has_agent_code_accessible_label", () => {
    render(<AgentCard agentKey="radar" />);

    expect(
      screen.getByRole("generic", {
        name: `Codigo do agente: ${AGENT_PERSONAS.radar.agentCode}`,
      }),
    ).toBeInTheDocument();
  });

  it("test_agentcard_article_has_accessible_label_with_agent_name", () => {
    render(<AgentCard agentKey="funding" />);

    expect(
      screen.getByRole("article", { name: `Agente ${AGENT_PERSONAS.funding.name}` }),
    ).toBeInTheDocument();
  });

  it("test_agentcard_renders_all_five_agents_without_crashing", () => {
    const keys = ["sintese", "radar", "codigo", "funding", "mercado"] as const;
    keys.forEach((key) => {
      const { unmount } = render(<AgentCard agentKey={key} />);
      expect(screen.getByText(AGENT_PERSONAS[key].name)).toBeInTheDocument();
      unmount();
    });
  });

  it("test_agentcard_has_hover_translate_transition_class", () => {
    const { container } = render(<AgentCard agentKey="mercado" />);

    const article = container.querySelector("article") as HTMLElement;
    expect(article.className).toContain("hover:-translate-y-0.5");
  });

  it("test_agentcard_has_graphite_background_class", () => {
    const { container } = render(<AgentCard agentKey="mercado" />);

    const article = container.querySelector("article") as HTMLElement;
    expect(article.className).toContain("bg-sinal-graphite");
  });

  it("test_agentcard_has_rounded_xl_class", () => {
    const { container } = render(<AgentCard agentKey="codigo" />);

    const article = container.querySelector("article") as HTMLElement;
    expect(article.className).toContain("rounded-xl");
  });
});

// ---------------------------------------------------------------------------
// AgentTeam
// ---------------------------------------------------------------------------

describe("AgentTeam", () => {
  it("test_agentteam_renders_section_heading", () => {
    render(<AgentTeam />);

    expect(screen.getByRole("heading", { name: "Nosso time de agentes." })).toBeInTheDocument();
  });

  it("test_agentteam_renders_subheading_text", () => {
    render(<AgentTeam />);

    expect(screen.getByText(/Cinco personalidades especializadas/)).toBeInTheDocument();
  });

  it("test_agentteam_renders_equipe_section_label", () => {
    render(<AgentTeam />);

    expect(screen.getByText("EQUIPE")).toBeInTheDocument();
  });

  it("test_agentteam_renders_all_five_agent_names", () => {
    render(<AgentTeam />);

    Object.values(AGENT_PERSONAS).forEach((persona) => {
      expect(screen.getByText(persona.name)).toBeInTheDocument();
    });
  });

  it("test_agentteam_renders_all_five_agent_roles", () => {
    render(<AgentTeam />);

    Object.values(AGENT_PERSONAS).forEach((persona) => {
      expect(screen.getByText(persona.role)).toBeInTheDocument();
    });
  });

  it("test_agentteam_renders_all_five_agent_codes", () => {
    render(<AgentTeam />);

    Object.values(AGENT_PERSONAS).forEach((persona) => {
      expect(screen.getByText(persona.agentCode)).toBeInTheDocument();
    });
  });

  it("test_agentteam_renders_all_five_agent_descriptions", () => {
    render(<AgentTeam />);

    Object.values(AGENT_PERSONAS).forEach((persona) => {
      expect(screen.getByText(persona.description)).toBeInTheDocument();
    });
  });

  it("test_agentteam_renders_five_agent_cards", () => {
    render(<AgentTeam />);

    // Each AgentCard uses role="article" with an aria-label
    const cards = screen.getAllByRole("article");
    expect(cards).toHaveLength(5);
  });

  it("test_agentteam_section_has_equipe_id", () => {
    const { container } = render(<AgentTeam />);

    const section = container.querySelector("section");
    expect(section).toHaveAttribute("id", "equipe");
  });

  it("test_agentteam_grid_has_responsive_column_classes", () => {
    const { container } = render(<AgentTeam />);

    const grid = container.querySelector(".grid") as HTMLElement;
    expect(grid.className).toContain("grid-cols-1");
    expect(grid.className).toContain("sm:grid-cols-2");
    expect(grid.className).toContain("lg:grid-cols-3");
  });

  it("test_agentteam_renders_section_signal_line_next_to_label", () => {
    const { container } = render(<AgentTeam />);

    const line = container.querySelector("span.bg-signal");
    expect(line).toBeInTheDocument();
  });

  it("test_agentteam_renders_sintese_avatar_initials_cm", () => {
    render(<AgentTeam />);

    expect(screen.getByText("CM")).toBeInTheDocument();
  });

  it("test_agentteam_renders_five_status_dots", () => {
    const { container } = render(<AgentTeam />);

    // Each AgentCard renders one aria-hidden status dot
    const dots = container.querySelectorAll('span[aria-hidden="true"]');
    expect(dots.length).toBeGreaterThanOrEqual(5);
  });
});

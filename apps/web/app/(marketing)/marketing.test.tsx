import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// Mock lucide-react icons before importing any component that pulls in Navbar
vi.mock("lucide-react", () => ({
  Menu: () => <span data-testid="menu-icon" />,
  X: () => <span data-testid="x-icon" />,
}));

import SobrePage, { metadata as sobreMetadata } from "./sobre/page";
import MetodologiaPage, { metadata as metodologiaMetadata } from "./metodologia/page";

// ---------------------------------------------------------------------------
// SobrePage
// ---------------------------------------------------------------------------

describe("SobrePage", () => {
  describe("page structure", () => {
    it("test_sobre_page_renders_navbar", () => {
      render(<SobrePage />);
      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });

    it("test_sobre_page_renders_footer", () => {
      render(<SobrePage />);
      expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    });

    it("test_sobre_page_renders_main_element", () => {
      render(<SobrePage />);
      expect(screen.getByRole("main")).toBeInTheDocument();
    });
  });

  describe("metadata export", () => {
    it("test_sobre_metadata_has_correct_title", () => {
      expect(sobreMetadata.title).toBe("Sobre o Sinal");
    });

    it("test_sobre_metadata_has_correct_description", () => {
      expect(sobreMetadata.description).toBe(
        "Inteligência aberta para quem constrói na América Latina.",
      );
    });

    it("test_sobre_metadata_has_opengraph_title", () => {
      expect((sobreMetadata.openGraph as { title: string }).title).toBe("Sobre o Sinal | Sinal");
    });

    it("test_sobre_metadata_opengraph_type_is_website", () => {
      expect((sobreMetadata.openGraph as { type: string }).type).toBe("website");
    });
  });

  describe("SOBRE section", () => {
    it("test_sobre_renders_section_label_sobre", () => {
      render(<SobrePage />);
      expect(screen.getByText("SOBRE")).toBeInTheDocument();
    });

    it("test_sobre_renders_h1_o_que_e_o_sinal", () => {
      render(<SobrePage />);
      expect(
        screen.getByRole("heading", { level: 1, name: "O que é o Sinal." }),
      ).toBeInTheDocument();
    });
  });

  describe("MISSAO section", () => {
    it("test_sobre_renders_section_label_missao", () => {
      render(<SobrePage />);
      expect(screen.getByText("MISSÃO")).toBeInTheDocument();
    });

    it("test_sobre_renders_h2_inteligencia_aberta", () => {
      render(<SobrePage />);
      expect(
        screen.getByRole("heading", { level: 2, name: "Inteligência aberta para quem constrói." }),
      ).toBeInTheDocument();
    });
  });

  describe("COMO FUNCIONA section", () => {
    it("test_sobre_renders_section_label_como_funciona", () => {
      render(<SobrePage />);
      expect(screen.getByText("COMO FUNCIONA")).toBeInTheDocument();
    });

    it("test_sobre_renders_h2_pesquisa_automatizada", () => {
      render(<SobrePage />);
      expect(
        screen.getByRole("heading", { level: 2, name: "Pesquisa automatizada, revisão humana." }),
      ).toBeInTheDocument();
    });

    it("test_sobre_renders_step_card_agentes_pesquisam", () => {
      render(<SobrePage />);
      expect(
        screen.getByRole("heading", { level: 3, name: "Agentes pesquisam" }),
      ).toBeInTheDocument();
    });

    it("test_sobre_renders_step_card_pipeline_filtra", () => {
      render(<SobrePage />);
      expect(
        screen.getByRole("heading", { level: 3, name: "Pipeline filtra" }),
      ).toBeInTheDocument();
    });

    it("test_sobre_renders_step_card_humanos_revisam", () => {
      render(<SobrePage />);
      expect(
        screen.getByRole("heading", { level: 3, name: "Humanos revisam" }),
      ).toBeInTheDocument();
    });

    it("test_sobre_renders_all_three_step_numbers", () => {
      render(<SobrePage />);
      expect(screen.getByText("01")).toBeInTheDocument();
      expect(screen.getByText("02")).toBeInTheDocument();
      expect(screen.getByText("03")).toBeInTheDocument();
    });

    it("test_sobre_renders_exactly_three_step_cards", () => {
      const { container } = render(<SobrePage />);
      // The three step cards are inside the 3-column grid within COMO FUNCIONA
      // Each card has an h3; count h3 elements inside <main>
      const main = container.querySelector("main");
      const h3s = main!.querySelectorAll("h3");
      expect(h3s).toHaveLength(3);
    });
  });

  describe("OS AGENTES section", () => {
    it("test_sobre_renders_section_label_os_agentes", () => {
      render(<SobrePage />);
      expect(screen.getByText("OS AGENTES")).toBeInTheDocument();
    });

    it("test_sobre_renders_h2_quem_pesquisa_o_sinal", () => {
      render(<SobrePage />);
      expect(
        screen.getByRole("heading", { level: 2, name: "Quem pesquisa o Sinal." }),
      ).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_name_clara_medeiros", () => {
      render(<SobrePage />);
      expect(screen.getByText("Clara Medeiros")).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_name_tomas_aguirre", () => {
      render(<SobrePage />);
      expect(screen.getByText("Tomás Aguirre")).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_name_marina_costa", () => {
      render(<SobrePage />);
      expect(screen.getByText("Marina Costa")).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_name_rafael_oliveira", () => {
      render(<SobrePage />);
      expect(screen.getByText("Rafael Oliveira")).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_name_valentina_rojas", () => {
      render(<SobrePage />);
      expect(screen.getByText("Valentina Rojas")).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_role_editora_chefe", () => {
      render(<SobrePage />);
      expect(screen.getByText("Editora-chefe")).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_role_analista_de_tendencias", () => {
      render(<SobrePage />);
      expect(screen.getByText("Analista de Tendências")).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_role_pesquisadora_de_tecnologia", () => {
      render(<SobrePage />);
      expect(screen.getByText("Pesquisadora de Tecnologia")).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_role_analista_de_investimentos", () => {
      render(<SobrePage />);
      expect(screen.getByText("Analista de Investimentos")).toBeInTheDocument();
    });

    it("test_sobre_renders_agent_role_especialista_latam", () => {
      render(<SobrePage />);
      expect(screen.getByText("Especialista LATAM")).toBeInTheDocument();
    });

    it("test_sobre_renders_all_five_agent_code_badges", () => {
      render(<SobrePage />);
      // agentCode.slice(0,2) produces: SI, RA, CO, FU, ME
      expect(screen.getByText("SI")).toBeInTheDocument();
      expect(screen.getByText("RA")).toBeInTheDocument();
      expect(screen.getByText("CO")).toBeInTheDocument();
      expect(screen.getByText("FU")).toBeInTheDocument();
      expect(screen.getByText("ME")).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// MetodologiaPage
// ---------------------------------------------------------------------------

describe("MetodologiaPage", () => {
  describe("page structure", () => {
    it("test_metodologia_page_renders_navbar", () => {
      render(<MetodologiaPage />);
      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });

    it("test_metodologia_page_renders_footer", () => {
      render(<MetodologiaPage />);
      expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    });

    it("test_metodologia_page_renders_main_element", () => {
      render(<MetodologiaPage />);
      expect(screen.getByRole("main")).toBeInTheDocument();
    });
  });

  describe("metadata export", () => {
    it("test_metodologia_metadata_has_correct_title", () => {
      expect(metodologiaMetadata.title).toBe("Metodologia");
    });

    it("test_metodologia_metadata_has_correct_description", () => {
      expect(metodologiaMetadata.description).toBe(
        "Como os agentes do Sinal pesquisam, validam e entregam inteligência.",
      );
    });

    it("test_metodologia_metadata_has_opengraph_title", () => {
      expect((metodologiaMetadata.openGraph as { title: string }).title).toBe(
        "Metodologia | Sinal",
      );
    });

    it("test_metodologia_metadata_opengraph_type_is_website", () => {
      expect((metodologiaMetadata.openGraph as { type: string }).type).toBe("website");
    });
  });

  describe("METODOLOGIA section", () => {
    it("test_metodologia_renders_section_label_metodologia", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("METODOLOGIA")).toBeInTheDocument();
    });

    it("test_metodologia_renders_h1_como_funciona_o_sinal", () => {
      render(<MetodologiaPage />);
      expect(
        screen.getByRole("heading", { level: 1, name: "Como funciona o Sinal." }),
      ).toBeInTheDocument();
    });
  });

  describe("PIPELINE section", () => {
    it("test_metodologia_renders_section_label_pipeline", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("PIPELINE")).toBeInTheDocument();
    });

    it("test_metodologia_renders_h2_6_etapas", () => {
      render(<MetodologiaPage />);
      expect(
        screen.getByRole("heading", { level: 2, name: "6 etapas, da fonte ao briefing." }),
      ).toBeInTheDocument();
    });

    it("test_metodologia_renders_step_title_coleta", () => {
      render(<MetodologiaPage />);
      expect(screen.getByRole("heading", { level: 3, name: "Coleta" })).toBeInTheDocument();
    });

    it("test_metodologia_renders_step_title_processamento", () => {
      render(<MetodologiaPage />);
      expect(screen.getByRole("heading", { level: 3, name: "Processamento" })).toBeInTheDocument();
    });

    it("test_metodologia_renders_step_title_validacao", () => {
      render(<MetodologiaPage />);
      expect(screen.getByRole("heading", { level: 3, name: "Validação" })).toBeInTheDocument();
    });

    it("test_metodologia_renders_step_title_filtragem_editorial", () => {
      render(<MetodologiaPage />);
      expect(
        screen.getByRole("heading", { level: 3, name: "Filtragem Editorial" }),
      ).toBeInTheDocument();
    });

    it("test_metodologia_renders_step_title_sintese", () => {
      render(<MetodologiaPage />);
      expect(screen.getByRole("heading", { level: 3, name: "Síntese" })).toBeInTheDocument();
    });

    it("test_metodologia_renders_step_title_revisao_humana", () => {
      render(<MetodologiaPage />);
      expect(screen.getByRole("heading", { level: 3, name: "Revisão Humana" })).toBeInTheDocument();
    });

    it("test_metodologia_renders_all_six_step_numbers", () => {
      render(<MetodologiaPage />);
      ["01", "02", "03", "04", "05", "06"].forEach((num) => {
        expect(screen.getByText(num)).toBeInTheDocument();
      });
    });

    it("test_metodologia_renders_exactly_six_pipeline_step_cards", () => {
      const { container } = render(<MetodologiaPage />);
      const main = container.querySelector("main");
      // Pipeline section has 6 h3 cards; DQ section has none (p tags for labels)
      const h3s = main!.querySelectorAll("h3");
      expect(h3s).toHaveLength(6);
    });
  });

  describe("SCORE DE QUALIDADE section", () => {
    it("test_metodologia_renders_section_label_score_de_qualidade", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("SCORE DE QUALIDADE")).toBeInTheDocument();
    });

    it("test_metodologia_renders_h2_dq_score", () => {
      render(<MetodologiaPage />);
      expect(
        screen.getByRole("heading", { level: 2, name: "DQ Score — Data Quality." }),
      ).toBeInTheDocument();
    });

    it("test_metodologia_renders_dq_grade_a", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("A")).toBeInTheDocument();
    });

    it("test_metodologia_renders_dq_grade_b", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("B")).toBeInTheDocument();
    });

    it("test_metodologia_renders_dq_grade_c", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("C")).toBeInTheDocument();
    });

    it("test_metodologia_renders_dq_grade_d", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("D")).toBeInTheDocument();
    });

    it("test_metodologia_renders_dq_label_verificado", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("Verificado")).toBeInTheDocument();
    });

    it("test_metodologia_renders_dq_label_plausivel", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("Plausível")).toBeInTheDocument();
    });

    it("test_metodologia_renders_dq_label_nao_verificado", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("Não verificado")).toBeInTheDocument();
    });

    it("test_metodologia_renders_dq_label_contradatorio", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("Contraditório")).toBeInTheDocument();
    });

    it("test_metodologia_renders_all_four_dq_grades", () => {
      render(<MetodologiaPage />);
      ["A", "B", "C", "D"].forEach((grade) => {
        expect(screen.getByText(grade)).toBeInTheDocument();
      });
    });
  });

  describe("TRANSPARENCIA section", () => {
    it("test_metodologia_renders_section_label_transparencia", () => {
      render(<MetodologiaPage />);
      expect(screen.getByText("TRANSPARÊNCIA")).toBeInTheDocument();
    });

    it("test_metodologia_renders_h2_cada_dado_rastreavel", () => {
      render(<MetodologiaPage />);
      expect(
        screen.getByRole("heading", { level: 2, name: "Cada dado, rastreável até a fonte." }),
      ).toBeInTheDocument();
    });

    it("test_metodologia_renders_github_link_with_correct_href", () => {
      render(<MetodologiaPage />);
      const link = screen.getByRole("link", { name: "Ver código no GitHub" });
      expect(link).toHaveAttribute("href", "https://github.com/fabianocruz/sinal-lab");
    });

    it("test_metodologia_github_link_opens_in_new_tab", () => {
      render(<MetodologiaPage />);
      const link = screen.getByRole("link", { name: "Ver código no GitHub" });
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    });

    it("test_metodologia_renders_log_de_correcoes_link", () => {
      render(<MetodologiaPage />);
      // "Log de Correções" appears in both the TRANSPARENCIA section and the
      // Footer column — assert at least one instance is present.
      const links = screen.getAllByRole("link", { name: "Log de Correções" });
      expect(links.length).toBeGreaterThanOrEqual(1);
    });
  });
});

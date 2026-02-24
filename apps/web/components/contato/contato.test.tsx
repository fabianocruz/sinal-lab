import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import ContatoForm from "./ContatoForm";

// Mock window.open for mailto
const openMock = vi.fn();
vi.stubGlobal("open", openMock);

describe("ContatoForm", () => {
  beforeEach(() => {
    openMock.mockClear();
  });

  // -------------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------------

  describe("initial render", () => {
    it("test_contato_renders_topic_buttons", () => {
      render(<ContatoForm />);
      expect(screen.getByText("Dúvida geral")).toBeInTheDocument();
      expect(screen.getByText("Reportar erro")).toBeInTheDocument();
      expect(screen.getByText("Parceria comercial")).toBeInTheDocument();
      expect(screen.getByText("Imprensa")).toBeInTheDocument();
      expect(screen.getByText("Requisição LGPD")).toBeInTheDocument();
      expect(screen.getByText("Problema técnico")).toBeInTheDocument();
    });

    it("test_contato_renders_name_input", () => {
      render(<ContatoForm />);
      expect(screen.getByPlaceholderText("Seu nome")).toBeInTheDocument();
    });

    it("test_contato_renders_email_input", () => {
      render(<ContatoForm />);
      expect(screen.getByPlaceholderText("seu@email.com")).toBeInTheDocument();
    });

    it("test_contato_renders_message_textarea", () => {
      render(<ContatoForm />);
      expect(screen.getByPlaceholderText("Sua mensagem...")).toBeInTheDocument();
    });

    it("test_contato_renders_submit_button", () => {
      render(<ContatoForm />);
      expect(screen.getByRole("button", { name: /Enviar mensagem/ })).toBeInTheDocument();
    });

    it("test_contato_renders_privacy_link", () => {
      render(<ContatoForm />);
      const link = screen.getByText("Política de Privacidade");
      expect(link).toBeInTheDocument();
      expect(link.closest("a")).toHaveAttribute("href", "/privacidade");
    });

    it("test_contato_renders_contact_email", () => {
      render(<ContatoForm />);
      expect(screen.getByText(/contato@sinal\.tech/)).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Submit button state
  // -------------------------------------------------------------------------

  describe("submit button state", () => {
    it("test_contato_submit_disabled_when_empty", () => {
      render(<ContatoForm />);
      const btn = screen.getByRole("button", { name: /Enviar mensagem/ });
      expect(btn).toBeDisabled();
    });

    it("test_contato_submit_disabled_without_topic", () => {
      render(<ContatoForm />);
      fireEvent.change(screen.getByPlaceholderText("seu@email.com"), {
        target: { value: "test@test.com" },
      });
      fireEvent.change(screen.getByPlaceholderText("Sua mensagem..."), {
        target: { value: "Hello" },
      });
      const btn = screen.getByRole("button", { name: /Enviar mensagem/ });
      expect(btn).toBeDisabled();
    });

    it("test_contato_submit_enabled_with_required_fields", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Dúvida geral"));
      fireEvent.change(screen.getByPlaceholderText("seu@email.com"), {
        target: { value: "test@test.com" },
      });
      fireEvent.change(screen.getByPlaceholderText("Sua mensagem..."), {
        target: { value: "Hello" },
      });
      const btn = screen.getByRole("button", { name: /Enviar mensagem/ });
      expect(btn).not.toBeDisabled();
    });
  });

  // -------------------------------------------------------------------------
  // Conditional fields
  // -------------------------------------------------------------------------

  describe("conditional fields", () => {
    it("test_contato_shows_lgpd_select_when_lgpd_topic_selected", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Requisição LGPD"));
      expect(screen.getByText("Selecione...")).toBeInTheDocument();
      expect(screen.getByText("Acesso aos meus dados")).toBeInTheDocument();
    });

    it("test_contato_shows_lgpd_disclaimer", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Requisição LGPD"));
      expect(screen.getByText(/Requisições LGPD respondidas em até 15 dias/)).toBeInTheDocument();
    });

    it("test_contato_lgpd_requires_type_for_submit", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Requisição LGPD"));
      fireEvent.change(screen.getByPlaceholderText("seu@email.com"), {
        target: { value: "test@test.com" },
      });
      fireEvent.change(screen.getByPlaceholderText(/requisição/i), {
        target: { value: "Quero acessar meus dados" },
      });
      // Submit should be disabled without LGPD type
      const btn = screen.getByRole("button", { name: /Enviar mensagem/ });
      expect(btn).toBeDisabled();
    });

    it("test_contato_shows_url_field_for_correcao_topic", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Reportar erro"));
      expect(screen.getByPlaceholderText("https://sinal.tech/artigos/...")).toBeInTheDocument();
    });

    it("test_contato_shows_company_field_for_parceria_topic", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Parceria comercial"));
      expect(screen.getByPlaceholderText("Nome da empresa")).toBeInTheDocument();
    });

    it("test_contato_shows_company_field_for_imprensa_topic", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Imprensa"));
      expect(screen.getByPlaceholderText("Nome da empresa")).toBeInTheDocument();
    });

    it("test_contato_hides_lgpd_fields_when_switching_topic", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Requisição LGPD"));
      expect(screen.getByText("Selecione...")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Dúvida geral"));
      expect(screen.queryByText("Selecione...")).not.toBeInTheDocument();
    });

    it("test_contato_changes_placeholder_per_topic", () => {
      render(<ContatoForm />);
      // Default placeholder
      expect(screen.getByPlaceholderText("Sua mensagem...")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Reportar erro"));
      expect(
        screen.getByPlaceholderText("Descreva o erro e indique a informação correta..."),
      ).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Submit flow
  // -------------------------------------------------------------------------

  describe("submit flow", () => {
    it("test_contato_opens_mailto_on_submit", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Dúvida geral"));
      fireEvent.change(screen.getByPlaceholderText("Seu nome"), {
        target: { value: "João" },
      });
      fireEvent.change(screen.getByPlaceholderText("seu@email.com"), {
        target: { value: "joao@test.com" },
      });
      fireEvent.change(screen.getByPlaceholderText("Sua mensagem..."), {
        target: { value: "Tenho uma dúvida" },
      });
      fireEvent.click(screen.getByRole("button", { name: /Enviar mensagem/ }));

      expect(openMock).toHaveBeenCalledTimes(1);
      const url = openMock.mock.calls[0][0] as string;
      expect(url).toContain("mailto:contato@sinal.tech");
      expect(url).toContain("subject=");
      expect(url).toContain("body=");
    });

    it("test_contato_shows_success_state_after_submit", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Dúvida geral"));
      fireEvent.change(screen.getByPlaceholderText("seu@email.com"), {
        target: { value: "test@test.com" },
      });
      fireEvent.change(screen.getByPlaceholderText("Sua mensagem..."), {
        target: { value: "Hello" },
      });
      fireEvent.click(screen.getByRole("button", { name: /Enviar mensagem/ }));

      expect(screen.getByText("Mensagem preparada.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Enviar outra/ })).toBeInTheDocument();
    });

    it("test_contato_resets_form_on_enviar_outra", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Dúvida geral"));
      fireEvent.change(screen.getByPlaceholderText("seu@email.com"), {
        target: { value: "test@test.com" },
      });
      fireEvent.change(screen.getByPlaceholderText("Sua mensagem..."), {
        target: { value: "Hello" },
      });
      fireEvent.click(screen.getByRole("button", { name: /Enviar mensagem/ }));

      // Click "Enviar outra"
      fireEvent.click(screen.getByRole("button", { name: /Enviar outra/ }));

      // Should be back to the form
      expect(screen.getByText("Dúvida geral")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("seu@email.com")).toBeInTheDocument();
      // Submit should be disabled again (form reset)
      const btn = screen.getByRole("button", { name: /Enviar mensagem/ });
      expect(btn).toBeDisabled();
    });

    it("test_contato_mailto_includes_tag_in_subject", () => {
      render(<ContatoForm />);
      fireEvent.click(screen.getByText("Problema técnico"));
      fireEvent.change(screen.getByPlaceholderText("seu@email.com"), {
        target: { value: "test@test.com" },
      });
      fireEvent.change(screen.getByPlaceholderText("Sua mensagem..."), {
        target: { value: "Bug report" },
      });
      fireEvent.click(screen.getByRole("button", { name: /Enviar mensagem/ }));

      const url = openMock.mock.calls[0][0] as string;
      expect(url).toContain(encodeURIComponent("[Bug]"));
    });
  });
});

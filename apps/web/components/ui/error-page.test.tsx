import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import ErrorPage from "@/components/ui/ErrorPage";

// ---------------------------------------------------------------------------
// Shared test fixture
// ---------------------------------------------------------------------------

const defaultProps = {
  error: new Error("Test error"),
  reset: vi.fn(),
  title: "Erro",
  message: "Algo deu errado no carregamento.",
  backHref: "/",
  backLabel: "Voltar ao início",
};

// ---------------------------------------------------------------------------
// ErrorPage
// ---------------------------------------------------------------------------

describe("ErrorPage", () => {
  it("test_errorpage_render_shows_title_in_eyebrow", () => {
    render(<ErrorPage {...defaultProps} />);

    expect(screen.getByText("Erro")).toBeInTheDocument();
  });

  it("test_errorpage_render_shows_fixed_heading_algo_deu_errado", () => {
    render(<ErrorPage {...defaultProps} />);

    expect(screen.getByRole("heading", { name: "Algo deu errado" })).toBeInTheDocument();
  });

  it("test_errorpage_render_shows_message_text", () => {
    render(<ErrorPage {...defaultProps} />);

    expect(screen.getByText("Algo deu errado no carregamento.")).toBeInTheDocument();
  });

  it("test_errorpage_render_shows_back_link_with_correct_href", () => {
    render(<ErrorPage {...defaultProps} />);

    const link = screen.getByRole("link", { name: "Voltar ao início" });
    expect(link).toHaveAttribute("href", "/");
  });

  it("test_errorpage_render_shows_back_link_with_correct_label", () => {
    render(<ErrorPage {...defaultProps} />);

    expect(screen.getByRole("link", { name: "Voltar ao início" })).toBeInTheDocument();
  });

  it("test_errorpage_render_shows_retry_button", () => {
    render(<ErrorPage {...defaultProps} />);

    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("test_errorpage_retry_button_calls_reset_on_click", () => {
    const reset = vi.fn();
    render(<ErrorPage {...defaultProps} reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("test_errorpage_render_custom_title_is_displayed", () => {
    render(<ErrorPage {...defaultProps} title="Edição não encontrada" />);

    expect(screen.getByText("Edição não encontrada")).toBeInTheDocument();
  });

  it("test_errorpage_render_custom_back_href_is_used", () => {
    render(<ErrorPage {...defaultProps} backHref="/newsletter" backLabel="Ver todas as edições" />);

    const link = screen.getByRole("link", { name: "Ver todas as edições" });
    expect(link).toHaveAttribute("href", "/newsletter");
  });

  it("test_errorpage_render_custom_back_label_is_displayed", () => {
    render(<ErrorPage {...defaultProps} backHref="/startups" backLabel="Ver todas as startups" />);

    expect(screen.getByRole("link", { name: "Ver todas as startups" })).toBeInTheDocument();
  });

  it("test_errorpage_retry_does_not_call_reset_before_click", () => {
    const reset = vi.fn();
    render(<ErrorPage {...defaultProps} reset={reset} />);

    expect(reset).not.toHaveBeenCalled();
  });

  it("test_errorpage_retry_button_calls_reset_exactly_once_per_click", () => {
    const reset = vi.fn();
    render(<ErrorPage {...defaultProps} reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(reset).toHaveBeenCalledTimes(2);
  });
});

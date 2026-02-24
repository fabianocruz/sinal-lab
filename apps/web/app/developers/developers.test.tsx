import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("next-auth/react", async () => {
  const actual = await vi.importActual<typeof import("next-auth/react")>("next-auth/react");
  return {
    ...actual,
    useSession: () => ({ data: null, status: "unauthenticated" }),
    SessionProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

vi.mock("@/lib/api", () => ({
  submitApiAccessRequest: vi.fn().mockResolvedValue({ message: "ok" }),
}));

import DevelopersPage from "./page";

// ===========================================================================
// DevelopersPage — Documentation Portal
// ===========================================================================

describe("DevelopersPage", () => {
  it("renders without crashing", () => {
    const { container } = render(<DevelopersPage />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the hero heading", () => {
    render(<DevelopersPage />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toContain("Dados LATAM Tech");
    expect(heading.textContent).toContain("via API REST");
  });

  it("renders both hero CTAs", () => {
    render(<DevelopersPage />);
    // "Solicitar Acesso" appears in hero CTA, sidebar, and form section
    const solicitar = screen.getAllByText(/Solicitar Acesso/);
    expect(solicitar.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Ver Endpoints")).toBeInTheDocument();
  });

  it("renders the Visão Geral section with heading", () => {
    render(<DevelopersPage />);
    // "Visão Geral" appears in sidebar + section label
    const matches = screen.getAllByText("Visão Geral");
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("APIs disponíveis.")).toBeInTheDocument();
  });

  it("renders all four API overview cards", () => {
    render(<DevelopersPage />);
    // API names appear in sidebar + overview cards + section headings
    const empresas = screen.getAllByText("Empresas");
    expect(empresas.length).toBeGreaterThanOrEqual(1);
    const conteudo = screen.getAllByText("Conteúdo");
    expect(conteudo.length).toBeGreaterThanOrEqual(1);
    const agentes = screen.getAllByText("Agentes");
    expect(agentes.length).toBeGreaterThanOrEqual(1);
    const investimentos = screen.getAllByText("Investimentos");
    expect(investimentos.length).toBeGreaterThanOrEqual(1);
  });

  it("renders Em breve badge on Funding card", () => {
    render(<DevelopersPage />);
    const badges = screen.getAllByText("Em breve");
    expect(badges.length).toBeGreaterThanOrEqual(1);
  });

  it("renders the Autenticação section", () => {
    render(<DevelopersPage />);
    // "Autenticação" appears in sidebar + section label
    const matches = screen.getAllByText("Autenticação");
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("API Key via header.")).toBeInTheDocument();
    expect(screen.getByText("Authorization: Bearer YOUR_API_KEY")).toBeInTheDocument();
  });

  it("renders all endpoint paths", () => {
    render(<DevelopersPage />);
    // Endpoint paths appear in EndpointBlock headers — may also appear in code examples
    const companies = screen.getAllByText("/api/companies");
    expect(companies.length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("/api/companies/{slug}").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("/api/content").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("/api/content/{slug}").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("/api/content/newsletter/latest").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("/api/agents/summary").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("/api/agents/runs").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("/api/funding").length).toBeGreaterThanOrEqual(1);
  });

  it("renders GET method badges", () => {
    render(<DevelopersPage />);
    const badges = screen.getAllByText("GET");
    expect(badges.length).toBeGreaterThanOrEqual(7);
  });

  it("renders the Paginação section", () => {
    render(<DevelopersPage />);
    const matches = screen.getAllByText(/Paginação/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Padrões compartilhados.")).toBeInTheDocument();
  });

  it("renders the Codigos de Erro section with error codes table", () => {
    render(<DevelopersPage />);
    const matches = screen.getAllByText(/Erros/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("200")).toBeInTheDocument();
    expect(screen.getByText("401")).toBeInTheDocument();
    expect(screen.getByText("404")).toBeInTheDocument();
  });

  it("renders the Solicitar Acesso section with form", () => {
    render(<DevelopersPage />);
    expect(screen.getByText("SOLICITAR ACESSO")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /solicitar acesso/i })).toBeInTheDocument();
  });

  it("renders sidebar navigation links", () => {
    render(<DevelopersPage />);
    const navs = screen.getAllByRole("navigation", { name: /navegação da documentação/i });
    expect(navs.length).toBeGreaterThanOrEqual(1);
  });

  it("renders section ids for anchor navigation", () => {
    const { container } = render(<DevelopersPage />);
    expect(container.querySelector("#visao-geral")).toBeInTheDocument();
    expect(container.querySelector("#autenticacao")).toBeInTheDocument();
    expect(container.querySelector("#empresas")).toBeInTheDocument();
    expect(container.querySelector("#conteudo")).toBeInTheDocument();
    expect(container.querySelector("#agentes")).toBeInTheDocument();
    expect(container.querySelector("#investimentos")).toBeInTheDocument();
    expect(container.querySelector("#paginacao")).toBeInTheDocument();
    expect(container.querySelector("#erros")).toBeInTheDocument();
    expect(container.querySelector("#solicitar-acesso")).toBeInTheDocument();
  });
});

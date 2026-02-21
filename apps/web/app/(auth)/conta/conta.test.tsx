import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// Mock lucide-react icons (used by AccountDetails)
vi.mock("lucide-react", () => ({
  LogOut: () => <span data-testid="logout-icon" />,
}));

import ContaPage, { metadata } from "./page";

// ===========================================================================
// ContaPage (server component — rendered synchronously in jsdom)
// ===========================================================================

describe("ContaPage", () => {
  it("test_contapage_renders_minha_conta_heading", () => {
    render(<ContaPage />);
    expect(screen.getByRole("heading", { name: "Minha conta" })).toBeInTheDocument();
  });

  it("test_contapage_renders_sinal_logo_linking_to_root", () => {
    render(<ContaPage />);
    const logoLink = screen.getByText("Sinal").closest("a");
    expect(logoLink).toHaveAttribute("href", "/");
  });

  it("test_contapage_renders_subtitle_text", () => {
    render(<ContaPage />);
    expect(screen.getByText(/Gerencie seus dados e preferências/i)).toBeInTheDocument();
  });

  it("test_contapage_metadata_has_correct_title", () => {
    expect(metadata.title).toBe("Minha conta | Sinal");
  });

  it("test_contapage_metadata_has_correct_description", () => {
    expect(metadata.description).toBe("Gerencie sua conta Sinal.");
  });
});

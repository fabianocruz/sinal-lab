import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CountryFilter from "@/components/startup/CountryFilter";

// ---------------------------------------------------------------------------
// CountryFilter
// ---------------------------------------------------------------------------

describe("CountryFilter", () => {
  it("renders all country buttons", () => {
    render(<CountryFilter />);
    expect(screen.getByText("Todos")).toBeInTheDocument();
    expect(screen.getByText("Brasil")).toBeInTheDocument();
    expect(screen.getByText("México")).toBeInTheDocument();
    expect(screen.getByText("Colômbia")).toBeInTheDocument();
    expect(screen.getByText("Argentina")).toBeInTheDocument();
    expect(screen.getByText("Chile")).toBeInTheDocument();
  });

  it("renders 6 buttons total", () => {
    render(<CountryFilter />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBe(6);
  });

  it("has accessible group label", () => {
    render(<CountryFilter />);
    expect(screen.getByRole("group", { name: /Filtrar por pa/ })).toBeInTheDocument();
  });

  it("todos is active by default (no country param)", () => {
    render(<CountryFilter />);
    const todosButton = screen.getByText("Todos").closest("button");
    expect(todosButton).toHaveAttribute("aria-pressed", "true");
  });

  it("other countries are inactive by default", () => {
    render(<CountryFilter />);
    const brasilButton = screen.getByText("Brasil").closest("button");
    expect(brasilButton).toHaveAttribute("aria-pressed", "false");
  });

  it("clicking a country button does not crash", () => {
    render(<CountryFilter />);
    const brasilButton = screen.getByText("Brasil").closest("button")!;
    expect(() => fireEvent.click(brasilButton)).not.toThrow();
  });

  it("clicking todos button does not crash", () => {
    render(<CountryFilter />);
    const todosButton = screen.getByText("Todos").closest("button")!;
    expect(() => fireEvent.click(todosButton)).not.toThrow();
  });

  it("each button has a flag emoji", () => {
    render(<CountryFilter />);
    const buttons = screen.getAllByRole("button");
    for (const button of buttons) {
      // Each button should have a span with the flag
      const flagSpan = button.querySelector("span");
      expect(flagSpan).not.toBeNull();
    }
  });
});

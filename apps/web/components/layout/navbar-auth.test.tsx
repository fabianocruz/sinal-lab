import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// next-auth/react mock — configurable per test via mockSessionData
// ---------------------------------------------------------------------------
let mockSessionData: { data: unknown; status: string } = {
  data: null,
  status: "unauthenticated",
};

vi.mock("next-auth/react", async () => {
  const actual = await vi.importActual<typeof import("next-auth/react")>("next-auth/react");
  return {
    ...actual,
    useSession: () => mockSessionData,
    SessionProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    signOut: vi.fn(),
  };
});

// Mock lucide-react icons (used by Navbar and UserMenu)
vi.mock("lucide-react", () => ({
  Menu: () => <span data-testid="menu-icon" />,
  X: () => <span data-testid="x-icon" />,
  LogOut: () => <span data-testid="logout-icon" />,
  User: () => <span data-testid="user-icon" />,
}));

import Navbar from "./Navbar";

// ===========================================================================
// Navbar — auth-aware CTA and auth state
// ===========================================================================

describe("Navbar auth-aware", () => {
  beforeEach(() => {
    mockSessionData = { data: null, status: "unauthenticated" };
  });

  // -------------------------------------------------------------------------
  // Unauthenticated — "Entrar" link + "Assine o Briefing" CTA
  // -------------------------------------------------------------------------

  describe("unauthenticated", () => {
    it("test_navbar_shows_entrar_link_when_unauthenticated", () => {
      render(<Navbar />);
      const entrarLinks = screen.getAllByRole("link", { name: "Entrar" });
      expect(entrarLinks.length).toBeGreaterThanOrEqual(1);
    });

    it("test_navbar_entrar_link_points_to_login", () => {
      render(<Navbar />);
      const entrarLinks = screen.getAllByRole("link", { name: "Entrar" });
      entrarLinks.forEach((link) => {
        expect(link).toHaveAttribute("href", "/login");
      });
    });

    it("test_navbar_shows_assine_o_briefing_cta_when_unauthenticated", () => {
      render(<Navbar />);
      const ctaLinks = screen.getAllByRole("link", { name: "Assine o Briefing" });
      expect(ctaLinks.length).toBeGreaterThanOrEqual(1);
    });

    it("test_navbar_assine_cta_points_to_hero_when_unauthenticated", () => {
      render(<Navbar />);
      const ctaLinks = screen.getAllByRole("link", { name: "Assine o Briefing" });
      ctaLinks.forEach((link) => {
        expect(link).toHaveAttribute("href", "/#hero");
      });
    });

    it("test_navbar_does_not_show_meu_briefing_when_unauthenticated", () => {
      render(<Navbar />);
      expect(screen.queryByRole("link", { name: "Meu Briefing" })).not.toBeInTheDocument();
    });

    it("test_navbar_does_not_show_user_avatar_when_unauthenticated", () => {
      render(<Navbar />);
      expect(screen.queryByRole("button", { name: "Menu da conta" })).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Authenticated — UserMenu avatar + "Meu Briefing" CTA
  // -------------------------------------------------------------------------

  describe("authenticated", () => {
    beforeEach(() => {
      mockSessionData = {
        data: {
          user: {
            name: "Fabiano Cruz",
            email: "fabiano@example.com",
          },
        },
        status: "authenticated",
      };
    });

    it("test_navbar_shows_user_avatar_when_authenticated", () => {
      render(<Navbar />);
      expect(screen.getByRole("button", { name: "Menu da conta" })).toBeInTheDocument();
    });

    it("test_navbar_shows_meu_briefing_cta_when_authenticated", () => {
      render(<Navbar />);
      const ctaLinks = screen.getAllByRole("link", { name: "Meu Briefing" });
      expect(ctaLinks.length).toBeGreaterThanOrEqual(1);
    });

    it("test_navbar_meu_briefing_points_to_newsletter_when_authenticated", () => {
      render(<Navbar />);
      const ctaLinks = screen.getAllByRole("link", { name: "Meu Briefing" });
      ctaLinks.forEach((link) => {
        expect(link).toHaveAttribute("href", "/newsletter");
      });
    });

    it("test_navbar_does_not_show_entrar_link_when_authenticated", () => {
      render(<Navbar />);
      expect(screen.queryByRole("link", { name: "Entrar" })).not.toBeInTheDocument();
    });

    it("test_navbar_does_not_show_assine_o_briefing_when_authenticated", () => {
      render(<Navbar />);
      expect(screen.queryByRole("link", { name: "Assine o Briefing" })).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe("loading", () => {
    beforeEach(() => {
      mockSessionData = { data: null, status: "loading" };
    });

    it("test_navbar_does_not_show_entrar_during_loading", () => {
      render(<Navbar />);
      expect(screen.queryByRole("link", { name: "Entrar" })).not.toBeInTheDocument();
    });

    it("test_navbar_does_not_show_user_avatar_during_loading", () => {
      render(<Navbar />);
      expect(screen.queryByRole("button", { name: "Menu da conta" })).not.toBeInTheDocument();
    });
  });
});

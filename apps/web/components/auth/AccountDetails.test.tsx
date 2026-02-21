import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// next-auth/react mock — configurable per test via mockSessionData
// ---------------------------------------------------------------------------
const mockSignOut = vi.fn();
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
    signOut: (...args: unknown[]) => mockSignOut(...args),
  };
});

// Mock lucide-react icons
vi.mock("lucide-react", () => ({
  LogOut: () => <span data-testid="logout-icon" />,
}));

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/conta",
  useSearchParams: () => new URLSearchParams(),
}));

import AccountDetails from "./AccountDetails";

// ===========================================================================
// AccountDetails
// ===========================================================================

describe("AccountDetails", () => {
  beforeEach(() => {
    mockSignOut.mockReset();
    mockPush.mockReset();
    mockSessionData = { data: null, status: "unauthenticated" };
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe("loading state", () => {
    it("test_accountdetails_shows_skeleton_while_loading", () => {
      mockSessionData = { data: null, status: "loading" };
      const { container } = render(<AccountDetails />);
      const skeletons = container.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBe(3);
    });
  });

  // -------------------------------------------------------------------------
  // Unauthenticated redirect
  // -------------------------------------------------------------------------

  describe("unauthenticated", () => {
    it("test_accountdetails_redirects_to_login_when_unauthenticated", () => {
      mockSessionData = { data: null, status: "unauthenticated" };
      render(<AccountDetails />);
      expect(mockPush).toHaveBeenCalledWith("/login");
    });

    it("test_accountdetails_renders_nothing_when_no_session", () => {
      mockSessionData = { data: null, status: "unauthenticated" };
      const { container } = render(<AccountDetails />);
      // After redirect effect, should render null (empty container)
      expect(container.innerHTML).toBe("");
    });
  });

  // -------------------------------------------------------------------------
  // Authenticated display
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

    it("test_accountdetails_renders_user_initial_in_avatar", () => {
      render(<AccountDetails />);
      expect(screen.getByText("F")).toBeInTheDocument();
    });

    it("test_accountdetails_renders_user_name", () => {
      render(<AccountDetails />);
      // Name appears in avatar area and in InfoRow
      const nameElements = screen.getAllByText("Fabiano Cruz");
      expect(nameElements.length).toBe(2);
    });

    it("test_accountdetails_renders_user_email", () => {
      render(<AccountDetails />);
      // Email appears in avatar area and in InfoRow
      const emailElements = screen.getAllByText("fabiano@example.com");
      expect(emailElements.length).toBe(2);
    });

    it("test_accountdetails_renders_email_info_row", () => {
      render(<AccountDetails />);
      expect(screen.getByText("Email")).toBeInTheDocument();
    });

    it("test_accountdetails_renders_nome_info_row", () => {
      render(<AccountDetails />);
      expect(screen.getByText("Nome")).toBeInTheDocument();
    });

    it("test_accountdetails_renders_status_info_row_with_ativo", () => {
      render(<AccountDetails />);
      expect(screen.getByText("Status")).toBeInTheDocument();
      expect(screen.getByText("Ativo")).toBeInTheDocument();
    });

    it("test_accountdetails_renders_sair_button", () => {
      render(<AccountDetails />);
      expect(screen.getByRole("button", { name: /Sair da conta/i })).toBeInTheDocument();
    });

    it("test_accountdetails_sair_calls_signout", () => {
      render(<AccountDetails />);
      screen.getByRole("button", { name: /Sair da conta/i }).click();
      expect(mockSignOut).toHaveBeenCalledWith({ callbackUrl: "/" });
    });

    it("test_accountdetails_does_not_redirect_when_authenticated", () => {
      render(<AccountDetails />);
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Edge cases
  // -------------------------------------------------------------------------

  describe("edge cases", () => {
    it("test_accountdetails_shows_nao_informado_when_name_is_null", () => {
      mockSessionData = {
        data: {
          user: {
            name: null,
            email: "fabiano@example.com",
          },
        },
        status: "authenticated",
      };
      render(<AccountDetails />);
      expect(screen.getByText("Não informado")).toBeInTheDocument();
    });

    it("test_accountdetails_avatar_uses_email_initial_when_name_is_null", () => {
      mockSessionData = {
        data: {
          user: {
            name: null,
            email: "fabiano@example.com",
          },
        },
        status: "authenticated",
      };
      render(<AccountDetails />);
      // Avatar should show "F" from email
      const avatars = screen.getAllByText("F");
      expect(avatars.length).toBeGreaterThanOrEqual(1);
    });

    it("test_accountdetails_shows_dash_when_email_is_null", () => {
      mockSessionData = {
        data: {
          user: {
            name: "Fabiano",
            email: null,
          },
        },
        status: "authenticated",
      };
      render(<AccountDetails />);
      expect(screen.getByText("—")).toBeInTheDocument();
    });
  });
});

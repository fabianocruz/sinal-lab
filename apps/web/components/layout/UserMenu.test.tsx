import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// next-auth/react mock — override to include signOut
// ---------------------------------------------------------------------------
const mockSignOut = vi.fn();

vi.mock("next-auth/react", async () => {
  const actual = await vi.importActual<typeof import("next-auth/react")>("next-auth/react");
  return {
    ...actual,
    useSession: () => ({ data: null, status: "unauthenticated" }),
    SessionProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    signOut: (...args: unknown[]) => mockSignOut(...args),
  };
});

// Mock lucide-react icons
vi.mock("lucide-react", () => ({
  LogOut: () => <span data-testid="logout-icon" />,
  User: () => <span data-testid="user-icon" />,
}));

import UserMenu from "./UserMenu";

// ===========================================================================
// UserMenu
// ===========================================================================

describe("UserMenu", () => {
  beforeEach(() => {
    mockSignOut.mockReset();
  });

  // -------------------------------------------------------------------------
  // Structure / rendering
  // -------------------------------------------------------------------------

  describe("structure", () => {
    it("test_usermenu_renders_avatar_button", () => {
      render(<UserMenu name="Fabiano Cruz" email="fabiano@example.com" />);
      expect(screen.getByRole("button", { name: "Menu da conta" })).toBeInTheDocument();
    });

    it("test_usermenu_avatar_shows_first_letter_of_name", () => {
      render(<UserMenu name="Fabiano Cruz" email="fabiano@example.com" />);
      expect(screen.getByRole("button", { name: "Menu da conta" })).toHaveTextContent("F");
    });

    it("test_usermenu_avatar_shows_first_letter_of_email_when_name_is_null", () => {
      render(<UserMenu name={null} email="test@example.com" />);
      expect(screen.getByRole("button", { name: "Menu da conta" })).toHaveTextContent("T");
    });

    it("test_usermenu_avatar_shows_U_when_both_name_and_email_are_null", () => {
      render(<UserMenu name={null} email={null} />);
      expect(screen.getByRole("button", { name: "Menu da conta" })).toHaveTextContent("U");
    });

    it("test_usermenu_dropdown_is_closed_by_default", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      expect(screen.queryByText("Minha conta")).not.toBeInTheDocument();
    });

    it("test_usermenu_avatar_has_aria_expanded_false_when_closed", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      expect(screen.getByRole("button", { name: "Menu da conta" })).toHaveAttribute(
        "aria-expanded",
        "false",
      );
    });
  });

  // -------------------------------------------------------------------------
  // Dropdown open
  // -------------------------------------------------------------------------

  describe("dropdown open", () => {
    it("test_usermenu_opens_dropdown_on_click", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      expect(screen.getByText("Minha conta")).toBeInTheDocument();
    });

    it("test_usermenu_shows_user_name_in_dropdown", () => {
      render(<UserMenu name="Fabiano Cruz" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      expect(screen.getByText("Fabiano Cruz")).toBeInTheDocument();
    });

    it("test_usermenu_shows_user_email_in_dropdown", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      expect(screen.getByText("fabiano@example.com")).toBeInTheDocument();
    });

    it("test_usermenu_does_not_show_name_when_null", () => {
      render(<UserMenu name={null} email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      // Only email should be visible, no empty name paragraph
      expect(screen.getByText("fabiano@example.com")).toBeInTheDocument();
    });

    it("test_usermenu_renders_minha_conta_link", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      const link = screen.getByRole("link", { name: /Minha conta/i });
      expect(link).toHaveAttribute("href", "/conta");
    });

    it("test_usermenu_renders_sair_button", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      expect(screen.getByRole("button", { name: /Sair/i })).toBeInTheDocument();
    });

    it("test_usermenu_aria_expanded_is_true_when_open", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      expect(screen.getByRole("button", { name: "Menu da conta" })).toHaveAttribute(
        "aria-expanded",
        "true",
      );
    });
  });

  // -------------------------------------------------------------------------
  // Dropdown close
  // -------------------------------------------------------------------------

  describe("dropdown close", () => {
    it("test_usermenu_closes_on_second_click", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      const avatar = screen.getByRole("button", { name: "Menu da conta" });
      fireEvent.click(avatar);
      expect(screen.getByText("Minha conta")).toBeInTheDocument();

      fireEvent.click(avatar);
      expect(screen.queryByText("Minha conta")).not.toBeInTheDocument();
    });

    it("test_usermenu_closes_on_escape_key", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      expect(screen.getByText("Minha conta")).toBeInTheDocument();

      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByText("Minha conta")).not.toBeInTheDocument();
    });

    it("test_usermenu_closes_on_click_outside", () => {
      render(
        <div>
          <span data-testid="outside">outside</span>
          <UserMenu name="Fabiano" email="fabiano@example.com" />
        </div>,
      );
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      expect(screen.getByText("Minha conta")).toBeInTheDocument();

      fireEvent.mouseDown(screen.getByTestId("outside"));
      expect(screen.queryByText("Minha conta")).not.toBeInTheDocument();
    });

    it("test_usermenu_closes_when_minha_conta_link_is_clicked", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      fireEvent.click(screen.getByRole("link", { name: /Minha conta/i }));
      expect(screen.queryByRole("link", { name: /Minha conta/i })).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Sign out
  // -------------------------------------------------------------------------

  describe("sign out", () => {
    it("test_usermenu_calls_signout_when_sair_is_clicked", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      fireEvent.click(screen.getByRole("button", { name: /Sair/i }));
      expect(mockSignOut).toHaveBeenCalledWith({ callbackUrl: "/" });
    });

    it("test_usermenu_calls_signout_with_correct_callback_url", () => {
      render(<UserMenu name="Fabiano" email="fabiano@example.com" />);
      fireEvent.click(screen.getByRole("button", { name: "Menu da conta" }));
      fireEvent.click(screen.getByRole("button", { name: /Sair/i }));
      expect(mockSignOut).toHaveBeenCalledTimes(1);
      expect(mockSignOut.mock.calls[0][0]).toEqual({ callbackUrl: "/" });
    });
  });
});

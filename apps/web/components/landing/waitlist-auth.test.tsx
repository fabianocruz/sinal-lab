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
  };
});

vi.mock("@/lib/api", () => ({
  submitWaitlist: vi.fn().mockResolvedValue({ message: "ok", email: "test@test.com" }),
}));

import WaitlistForm from "./WaitlistForm";

// ===========================================================================
// WaitlistForm — auth-aware behaviour
// ===========================================================================

describe("WaitlistForm auth-aware", () => {
  beforeEach(() => {
    mockSessionData = { data: null, status: "unauthenticated" };
  });

  // -------------------------------------------------------------------------
  // Unauthenticated — shows form
  // -------------------------------------------------------------------------

  describe("unauthenticated", () => {
    it("test_waitlistform_shows_email_input_when_unauthenticated", () => {
      render(<WaitlistForm />);
      expect(screen.getByPlaceholderText("seu@email.com")).toBeInTheDocument();
    });

    it("test_waitlistform_shows_submit_button_when_unauthenticated", () => {
      render(<WaitlistForm />);
      expect(screen.getByRole("button", { name: "Assine o Briefing" })).toBeInTheDocument();
    });

    it("test_waitlistform_does_not_show_already_subscribed_message", () => {
      render(<WaitlistForm />);
      expect(screen.queryByText(/Você já recebe o Briefing/i)).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Authenticated — shows "already subscribed" message
  // -------------------------------------------------------------------------

  describe("authenticated", () => {
    beforeEach(() => {
      mockSessionData = {
        data: {
          user: { name: "Fabiano", email: "fabiano@example.com" },
        },
        status: "authenticated",
      };
    });

    it("test_waitlistform_shows_already_subscribed_message_when_authenticated", () => {
      render(<WaitlistForm />);
      expect(screen.getByText(/Você já recebe o Briefing!/i)).toBeInTheDocument();
    });

    it("test_waitlistform_shows_link_to_newsletter_archive_when_authenticated", () => {
      render(<WaitlistForm />);
      const link = screen.getByRole("link", { name: /Confira as últimas edições/i });
      expect(link).toHaveAttribute("href", "/newsletter");
    });

    it("test_waitlistform_hides_email_input_when_authenticated", () => {
      render(<WaitlistForm />);
      expect(screen.queryByPlaceholderText("seu@email.com")).not.toBeInTheDocument();
    });

    it("test_waitlistform_hides_submit_button_when_authenticated", () => {
      render(<WaitlistForm />);
      expect(screen.queryByRole("button", { name: "Assine o Briefing" })).not.toBeInTheDocument();
    });

    it("test_waitlistform_shows_checkmark_when_authenticated", () => {
      render(<WaitlistForm />);
      expect(screen.getByText("✓")).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Loading — shows placeholder
  // -------------------------------------------------------------------------

  describe("loading", () => {
    it("test_waitlistform_shows_placeholder_during_auth_loading", () => {
      mockSessionData = { data: null, status: "loading" };
      const { container } = render(<WaitlistForm />);
      // Placeholder div has specific height class
      const placeholder = container.querySelector(".h-\\[56px\\]");
      expect(placeholder).toBeInTheDocument();
    });

    it("test_waitlistform_hides_form_during_auth_loading", () => {
      mockSessionData = { data: null, status: "loading" };
      render(<WaitlistForm />);
      expect(screen.queryByPlaceholderText("seu@email.com")).not.toBeInTheDocument();
    });

    it("test_waitlistform_hides_already_subscribed_during_auth_loading", () => {
      mockSessionData = { data: null, status: "loading" };
      render(<WaitlistForm />);
      expect(screen.queryByText(/Você já recebe o Briefing/i)).not.toBeInTheDocument();
    });
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WaitlistForm from "./WaitlistForm";
import * as api from "../lib/api";

// Mock the API module
vi.mock("../lib/api", () => ({
  submitWaitlist: vi.fn(),
}));

describe("WaitlistForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Initial render", () => {
    it("should render email input field", () => {
      render(<WaitlistForm />);
      const input = screen.getByPlaceholderText("seu@email.com");
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute("type", "email");
    });

    it("should render submit button with correct text", () => {
      render(<WaitlistForm />);
      const button = screen.getByRole("button", { name: /assinar grátis/i });
      expect(button).toBeInTheDocument();
    });

    it("should render disclaimer text", () => {
      render(<WaitlistForm />);
      const disclaimer = screen.getByText(/sem spam/i);
      expect(disclaimer).toBeInTheDocument();
      expect(screen.getByText(/100% gratuito/i)).toBeInTheDocument();
    });

    it("should have empty email input initially", () => {
      render(<WaitlistForm />);
      const input = screen.getByPlaceholderText("seu@email.com");
      expect(input).toHaveValue("");
    });
  });

  describe("Email validation", () => {
    it("should show error when email is empty", async () => {
      const user = userEvent.setup();
      render(<WaitlistForm />);

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/por favor, insira um email válido/i)).toBeInTheDocument();
      });
    });

    it("should show error when email is invalid (no @)", async () => {
      const user = userEvent.setup();
      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "invalidemail");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/por favor, insira um email válido/i)).toBeInTheDocument();
      });
    });

    it("should not show error for valid email format", async () => {
      const user = userEvent.setup();
      vi.mocked(api.submitWaitlist).mockResolvedValueOnce({
        message: "Success",
        email: "valid@email.com",
        position: 100,
      });

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "valid@email.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.queryByText(/por favor, insira um email válido/i)).not.toBeInTheDocument();
      });
    });
  });

  describe("Form submission", () => {
    it("should call submitWaitlist with email on valid submission", async () => {
      const user = userEvent.setup();
      const mockResponse = {
        message: "Voce esta na lista!",
        email: "test@example.com",
        position: 250,
      };
      vi.mocked(api.submitWaitlist).mockResolvedValueOnce(mockResponse);

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "test@example.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(api.submitWaitlist).toHaveBeenCalledWith({
          email: "test@example.com",
        });
      });
    });

    it("should show loading state during submission", async () => {
      const user = userEvent.setup();
      let resolveSubmit: (value: any) => void;
      const submitPromise = new Promise((resolve) => {
        resolveSubmit = resolve;
      });
      vi.mocked(api.submitWaitlist).mockReturnValueOnce(submitPromise);

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "test@example.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/enviando/i)).toBeInTheDocument();
      });

      // Resolve the promise to cleanup
      resolveSubmit!({
        message: "Success",
        email: "test@example.com",
        position: 1,
      });
    });

    it("should disable input during submission", async () => {
      const user = userEvent.setup();
      let resolveSubmit: (value: any) => void;
      const submitPromise = new Promise((resolve) => {
        resolveSubmit = resolve;
      });
      vi.mocked(api.submitWaitlist).mockReturnValueOnce(submitPromise);

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com") as HTMLInputElement;
      await user.type(input, "test@example.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(input.disabled).toBe(true);
      });

      // Resolve the promise to cleanup
      resolveSubmit!({
        message: "Success",
        email: "test@example.com",
        position: 1,
      });
    });
  });

  describe("Success state", () => {
    it("should show success message after successful submission", async () => {
      const user = userEvent.setup();
      const mockResponse = {
        message: "Voce esta na lista!",
        email: "success@example.com",
        position: 100,
      };
      vi.mocked(api.submitWaitlist).mockResolvedValueOnce(mockResponse);

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "success@example.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/você está na lista/i)).toBeInTheDocument();
      });
    });

    it("should display position in waitlist", async () => {
      const user = userEvent.setup();
      const mockResponse = {
        message: "Success",
        email: "test@example.com",
        position: 250,
      };
      vi.mocked(api.submitWaitlist).mockResolvedValueOnce(mockResponse);

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "test@example.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/#250/)).toBeInTheDocument();
      });
    });

    it("should hide form and show success UI", async () => {
      const user = userEvent.setup();
      const mockResponse = {
        message: "Success",
        email: "test@example.com",
        position: 100,
      };
      vi.mocked(api.submitWaitlist).mockResolvedValueOnce(mockResponse);

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "test@example.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.queryByPlaceholderText("seu@email.com")).not.toBeInTheDocument();
        expect(screen.getByText(/você está na lista/i)).toBeInTheDocument();
      });
    });

    it("should allow resetting to idle state from success", async () => {
      const user = userEvent.setup();
      const mockResponse = {
        message: "Success",
        email: "test@example.com",
        position: 100,
      };
      vi.mocked(api.submitWaitlist).mockResolvedValueOnce(mockResponse);

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "test@example.com");

      const submitButton = screen.getByRole("button", {
        name: /assinar grátis/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/você está na lista/i)).toBeInTheDocument();
      });

      const resetButton = screen.getByRole("button", {
        name: /cadastrar outro email/i,
      });
      await user.click(resetButton);

      await waitFor(() => {
        expect(screen.getByPlaceholderText("seu@email.com")).toBeInTheDocument();
        expect(screen.queryByText(/você está na lista/i)).not.toBeInTheDocument();
      });
    });
  });

  describe("Error state", () => {
    it("should show error message when API call fails", async () => {
      const user = userEvent.setup();
      vi.mocked(api.submitWaitlist).mockRejectedValueOnce(
        new Error("Email ja cadastrado na waitlist."),
      );

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "duplicate@example.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/email ja cadastrado na waitlist/i)).toBeInTheDocument();
      });
    });

    it("should show generic error for non-Error exceptions", async () => {
      const user = userEvent.setup();
      vi.mocked(api.submitWaitlist).mockRejectedValueOnce("Unknown error string");

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "test@example.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/erro ao cadastrar. tente novamente/i)).toBeInTheDocument();
      });
    });

    it("should clear error message when submitting again", async () => {
      const user = userEvent.setup();
      vi.mocked(api.submitWaitlist)
        .mockRejectedValueOnce(new Error("First error"))
        .mockResolvedValueOnce({
          message: "Success",
          email: "test@example.com",
          position: 100,
        });

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "test@example.com");

      const button = screen.getByRole("button", { name: /assinar grátis/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/first error/i)).toBeInTheDocument();
      });

      // Clear and retry
      await user.clear(input);
      await user.type(input, "new@example.com");
      await user.click(button);

      await waitFor(() => {
        expect(screen.queryByText(/first error/i)).not.toBeInTheDocument();
      });
    });
  });

  describe("Accessibility", () => {
    it("should have required attribute on email input", () => {
      render(<WaitlistForm />);
      const input = screen.getByPlaceholderText("seu@email.com");
      expect(input).toBeRequired();
    });

    it("should have proper button role", () => {
      render(<WaitlistForm />);
      const button = screen.getByRole("button", { name: /assinar grátis/i });
      expect(button).toBeInTheDocument();
    });

    it("should handle form submission via Enter key", async () => {
      const user = userEvent.setup();
      const mockResponse = {
        message: "Success",
        email: "test@example.com",
        position: 100,
      };
      vi.mocked(api.submitWaitlist).mockResolvedValueOnce(mockResponse);

      render(<WaitlistForm />);

      const input = screen.getByPlaceholderText("seu@email.com");
      await user.type(input, "test@example.com{Enter}");

      await waitFor(() => {
        expect(api.submitWaitlist).toHaveBeenCalled();
      });
    });
  });
});

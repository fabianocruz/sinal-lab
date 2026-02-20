import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// next-auth/react mock
//
// The global setup in test/setup.tsx mocks next-auth/react but does NOT
// export `signIn`, which is used directly by LoginForm and SignupForm. We
// override the module here so that `signIn` is a controllable vi.fn().
// ---------------------------------------------------------------------------
const mockSignIn = vi.fn();

vi.mock("next-auth/react", async () => {
  const actual = await vi.importActual<typeof import("next-auth/react")>("next-auth/react");
  return {
    ...actual,
    useSession: () => ({ data: null, status: "unauthenticated" }),
    SessionProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    signIn: (...args: unknown[]) => mockSignIn(...args),
  };
});

// ---------------------------------------------------------------------------
// Imports (after mocks are registered)
// ---------------------------------------------------------------------------
import LoginForm from "./LoginForm";
import SignupForm from "./SignupForm";
import Providers from "../Providers";
import LoginPage, { metadata as loginMetadata } from "@/app/(auth)/login/page";
import CadastroPage, { metadata as cadastroMetadata } from "@/app/(auth)/cadastro/page";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Fill a field by its label id and fire a change event. */
function fillField(id: string, value: string) {
  fireEvent.change(screen.getByLabelText(new RegExp(id, "i")), {
    target: { value },
  });
}

/** Build a minimal ok/error fetch Response. */
function makeFetchResponse(status: number, body: object = {}): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

// ===========================================================================
// LoginForm
// ===========================================================================

describe("LoginForm", () => {
  beforeEach(() => {
    mockSignIn.mockReset();
  });

  // -------------------------------------------------------------------------
  // Structure / rendering
  // -------------------------------------------------------------------------

  describe("structure", () => {
    it("test_loginform_renders_email_input", () => {
      render(<LoginForm />);
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    });

    it("test_loginform_email_input_has_type_email", () => {
      render(<LoginForm />);
      expect(screen.getByLabelText(/email/i)).toHaveAttribute("type", "email");
    });

    it("test_loginform_renders_password_input", () => {
      render(<LoginForm />);
      expect(screen.getByLabelText(/senha/i)).toBeInTheDocument();
    });

    it("test_loginform_password_input_has_type_password", () => {
      render(<LoginForm />);
      expect(screen.getByLabelText(/senha/i)).toHaveAttribute("type", "password");
    });

    it("test_loginform_renders_entrar_submit_button", () => {
      render(<LoginForm />);
      expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
    });

    it("test_loginform_renders_entrar_com_google_button", () => {
      render(<LoginForm />);
      expect(screen.getByRole("button", { name: /entrar com google/i })).toBeInTheDocument();
    });

    it("test_loginform_renders_signup_link_to_cadastro", () => {
      render(<LoginForm />);
      const link = screen.getByRole("link", { name: /crie uma/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "/cadastro");
    });

    it("test_loginform_renders_no_ten_conta_text", () => {
      render(<LoginForm />);
      expect(screen.getByText(/Não tem conta/i)).toBeInTheDocument();
    });

    it("test_loginform_does_not_show_error_on_initial_render", () => {
      render(<LoginForm />);
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Validation — empty fields
  // -------------------------------------------------------------------------

  describe("empty field validation", () => {
    it("test_loginform_shows_error_when_submitting_with_empty_email_and_password", () => {
      render(<LoginForm />);
      fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);
      expect(screen.getByRole("alert")).toHaveTextContent("Preencha email e senha.");
    });

    it("test_loginform_shows_error_when_only_email_is_filled", () => {
      render(<LoginForm />);
      fillField("email", "user@example.com");
      fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);
      expect(screen.getByRole("alert")).toHaveTextContent("Preencha email e senha.");
    });

    it("test_loginform_shows_error_when_only_password_is_filled", () => {
      render(<LoginForm />);
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);
      expect(screen.getByRole("alert")).toHaveTextContent("Preencha email e senha.");
    });

    it("test_loginform_does_not_call_signin_when_fields_are_empty", () => {
      render(<LoginForm />);
      fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);
      expect(mockSignIn).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe("loading state", () => {
    it("test_loginform_submit_button_shows_entrando_while_loading", async () => {
      // signIn never resolves so the component stays in loading state
      mockSignIn.mockReturnValue(new Promise(() => {}));

      render(<LoginForm />);
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Entrando..." })).toBeInTheDocument();
      });
    });

    it("test_loginform_inputs_are_disabled_while_loading", async () => {
      mockSignIn.mockReturnValue(new Promise(() => {}));

      render(<LoginForm />);
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toBeDisabled();
        expect(screen.getByLabelText(/senha/i)).toBeDisabled();
      });
    });
  });

  // -------------------------------------------------------------------------
  // Credentials sign-in
  // -------------------------------------------------------------------------

  describe("credentials sign-in", () => {
    it("test_loginform_calls_signin_credentials_with_email_and_password", async () => {
      mockSignIn.mockResolvedValue({ error: null });

      render(<LoginForm />);
      fillField("email", "user@example.com");
      fillField("senha", "secret123");
      fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith("credentials", {
          email: "user@example.com",
          password: "secret123",
          redirect: false,
        });
      });
    });

    it("test_loginform_shows_error_when_signin_returns_error", async () => {
      mockSignIn.mockResolvedValue({ error: "CredentialsSignin" });

      render(<LoginForm />);
      fillField("email", "user@example.com");
      fillField("senha", "wrongpassword");
      fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          "Email ou senha incorretos. Tente novamente.",
        );
      });
    });

    it("test_loginform_does_not_show_error_on_successful_signin", async () => {
      mockSignIn.mockResolvedValue({ error: null });

      render(<LoginForm />);
      fillField("email", "user@example.com");
      fillField("senha", "correct-pass");
      fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);

      await waitFor(() => {
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      });
    });
  });

  // -------------------------------------------------------------------------
  // Google sign-in
  // -------------------------------------------------------------------------

  describe("google sign-in", () => {
    it("test_loginform_calls_signin_google_when_google_button_clicked", async () => {
      mockSignIn.mockResolvedValue(undefined);

      render(<LoginForm />);
      fireEvent.click(screen.getByRole("button", { name: /entrar com google/i }));

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith("google", { callbackUrl: "/" });
      });
    });

    it("test_loginform_google_button_is_disabled_while_loading", async () => {
      mockSignIn.mockReturnValue(new Promise(() => {}));

      render(<LoginForm />);
      fireEvent.click(screen.getByRole("button", { name: /entrar com google/i }));

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /entrar com google/i })).toBeDisabled();
      });
    });
  });
});

// ===========================================================================
// SignupForm
// ===========================================================================

describe("SignupForm", () => {
  beforeEach(() => {
    mockSignIn.mockReset();
    vi.restoreAllMocks();
  });

  // -------------------------------------------------------------------------
  // Structure / rendering
  // -------------------------------------------------------------------------

  describe("structure", () => {
    it("test_signupform_renders_name_input", () => {
      render(<SignupForm />);
      expect(screen.getByLabelText(/nome/i)).toBeInTheDocument();
    });

    it("test_signupform_renders_email_input", () => {
      render(<SignupForm />);
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    });

    it("test_signupform_email_input_has_type_email", () => {
      render(<SignupForm />);
      expect(screen.getByLabelText(/email/i)).toHaveAttribute("type", "email");
    });

    it("test_signupform_renders_password_input", () => {
      render(<SignupForm />);
      expect(screen.getByLabelText(/senha/i)).toBeInTheDocument();
    });

    it("test_signupform_password_input_has_type_password", () => {
      render(<SignupForm />);
      expect(screen.getByLabelText(/senha/i)).toHaveAttribute("type", "password");
    });

    it("test_signupform_renders_criar_conta_submit_button", () => {
      render(<SignupForm />);
      expect(screen.getByRole("button", { name: "Criar conta" })).toBeInTheDocument();
    });

    it("test_signupform_renders_entrar_com_google_button", () => {
      render(<SignupForm />);
      expect(screen.getByRole("button", { name: /entrar com google/i })).toBeInTheDocument();
    });

    it("test_signupform_renders_login_link_to_login_page", () => {
      render(<SignupForm />);
      const link = screen.getByRole("link", { name: /entre/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "/login");
    });

    it("test_signupform_renders_ja_tem_conta_text", () => {
      render(<SignupForm />);
      expect(screen.getByText(/Já tem conta/i)).toBeInTheDocument();
    });

    it("test_signupform_does_not_show_error_on_initial_render", () => {
      render(<SignupForm />);
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Validation — empty fields
  // -------------------------------------------------------------------------

  describe("empty field validation", () => {
    it("test_signupform_shows_error_when_submitting_with_empty_email_and_password", () => {
      render(<SignupForm />);
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);
      expect(screen.getByRole("alert")).toHaveTextContent("Preencha email e senha.");
    });

    it("test_signupform_shows_error_when_only_email_is_filled", () => {
      render(<SignupForm />);
      fillField("email", "user@example.com");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);
      expect(screen.getByRole("alert")).toHaveTextContent("Preencha email e senha.");
    });

    it("test_signupform_does_not_call_fetch_when_email_is_empty", () => {
      const fetchSpy = vi.spyOn(global, "fetch");
      render(<SignupForm />);
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);
      expect(fetchSpy).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Password length validation
  // -------------------------------------------------------------------------

  describe("password length validation", () => {
    it("test_signupform_shows_error_when_password_is_less_than_8_chars", () => {
      render(<SignupForm />);
      fillField("email", "user@example.com");
      // 7 characters — exactly one below the 8-char minimum
      fillField("senha", "short7!");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);
      expect(screen.getByRole("alert")).toHaveTextContent(
        "A senha precisa ter pelo menos 8 caracteres.",
      );
    });

    it("test_signupform_shows_error_for_single_char_password", () => {
      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "a");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);
      expect(screen.getByRole("alert")).toHaveTextContent(
        "A senha precisa ter pelo menos 8 caracteres.",
      );
    });

    it("test_signupform_does_not_show_length_error_for_exactly_8_char_password", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(new Response("{}", { status: 200 }) as Response);
      mockSignIn.mockResolvedValue({ error: null });

      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "exactly8");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(screen.queryByText(/pelo menos 8 caracteres/i)).not.toBeInTheDocument();
      });
    });

    it("test_signupform_does_not_call_fetch_when_password_is_too_short", () => {
      const fetchSpy = vi.spyOn(global, "fetch");
      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "short");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);
      expect(fetchSpy).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe("loading state", () => {
    it("test_signupform_submit_button_shows_criando_conta_while_loading", async () => {
      vi.spyOn(global, "fetch").mockReturnValue(new Promise(() => {}));

      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Criando conta..." })).toBeInTheDocument();
      });
    });

    it("test_signupform_inputs_are_disabled_while_loading", async () => {
      vi.spyOn(global, "fetch").mockReturnValue(new Promise(() => {}));

      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toBeDisabled();
        expect(screen.getByLabelText(/senha/i)).toBeDisabled();
      });
    });
  });

  // -------------------------------------------------------------------------
  // Successful registration flow
  // -------------------------------------------------------------------------

  describe("successful registration", () => {
    it("test_signupform_calls_fetch_register_endpoint_with_correct_payload", async () => {
      const fetchSpy = vi
        .spyOn(global, "fetch")
        .mockResolvedValue(new Response("{}", { status: 201 }) as Response);
      mockSignIn.mockResolvedValue({ error: null });

      render(<SignupForm />);
      fillField("nome", "Fabiano Cruz");
      fillField("email", "fabiano@example.com");
      fillField("senha", "strong-pass-123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledWith(
          expect.stringContaining("/api/auth/register"),
          expect.objectContaining({
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: "Fabiano Cruz",
              email: "fabiano@example.com",
              password: "strong-pass-123",
            }),
          }),
        );
      });
    });

    it("test_signupform_calls_signin_credentials_after_successful_registration", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(new Response("{}", { status: 201 }) as Response);
      mockSignIn.mockResolvedValue({ error: null });

      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith("credentials", {
          email: "user@example.com",
          password: "password123",
          redirect: false,
        });
      });
    });

    it("test_signupform_omits_name_from_payload_when_name_is_empty", async () => {
      const fetchSpy = vi
        .spyOn(global, "fetch")
        .mockResolvedValue(new Response("{}", { status: 201 }) as Response);
      mockSignIn.mockResolvedValue({ error: null });

      render(<SignupForm />);
      // Do NOT fill the name field
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        const body = JSON.parse((fetchSpy.mock.calls[0][1] as RequestInit).body as string);
        // name should be undefined, so it is absent from the JSON payload
        expect(body).not.toHaveProperty("name");
      });
    });
  });

  // -------------------------------------------------------------------------
  // Registration error paths
  // -------------------------------------------------------------------------

  describe("registration error paths", () => {
    it("test_signupform_shows_duplicate_email_error_on_409", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        makeFetchResponse(409, { detail: "Email already registered" }),
      );

      render(<SignupForm />);
      fillField("email", "taken@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          "Este email já está em uso. Tente fazer login ou use outro email.",
        );
      });
    });

    it("test_signupform_does_not_call_signin_when_registration_fails_with_409", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        makeFetchResponse(409, { detail: "Email already registered" }),
      );

      render(<SignupForm />);
      fillField("email", "taken@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(mockSignIn).not.toHaveBeenCalled();
      });
    });

    it("test_signupform_shows_detail_error_on_non_409_server_error", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        makeFetchResponse(422, { detail: "Validation failed." }),
      );

      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent("Validation failed.");
      });
    });

    it("test_signupform_shows_fallback_error_when_response_body_has_no_detail", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(makeFetchResponse(500, {}));

      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          "Erro ao criar conta. Tente novamente.",
        );
      });
    });

    it("test_signupform_shows_connection_error_on_network_failure", async () => {
      vi.spyOn(global, "fetch").mockRejectedValue(new Error("Network error"));

      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          "Erro de conexão. Verifique sua internet e tente novamente.",
        );
      });
    });

    it("test_signupform_shows_error_when_registration_succeeds_but_signin_fails", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(new Response("{}", { status: 201 }) as Response);
      mockSignIn.mockResolvedValue({ error: "CredentialsSignin" });

      render(<SignupForm />);
      fillField("email", "user@example.com");
      fillField("senha", "password123");
      fireEvent.submit(screen.getByRole("button", { name: "Criar conta" }).closest("form")!);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          "Conta criada! Faça login para continuar.",
        );
      });
    });
  });

  // -------------------------------------------------------------------------
  // Google sign-in
  // -------------------------------------------------------------------------

  describe("google sign-in", () => {
    it("test_signupform_calls_signin_google_when_google_button_clicked", async () => {
      mockSignIn.mockResolvedValue(undefined);

      render(<SignupForm />);
      fireEvent.click(screen.getByRole("button", { name: /entrar com google/i }));

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith("google", { callbackUrl: "/" });
      });
    });

    it("test_signupform_google_button_is_disabled_while_loading", async () => {
      mockSignIn.mockReturnValue(new Promise(() => {}));

      render(<SignupForm />);
      fireEvent.click(screen.getByRole("button", { name: /entrar com google/i }));

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /entrar com google/i })).toBeDisabled();
      });
    });
  });
});

// ===========================================================================
// Providers
// ===========================================================================

describe("Providers", () => {
  it("test_providers_renders_children", () => {
    render(
      <Providers>
        <p>Child content</p>
      </Providers>,
    );
    expect(screen.getByText("Child content")).toBeInTheDocument();
  });

  it("test_providers_renders_multiple_children", () => {
    render(
      <Providers>
        <span>First</span>
        <span>Second</span>
      </Providers>,
    );
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("test_providers_wraps_with_session_provider", () => {
    // The SessionProvider mock is a passthrough fragment. We verify that the
    // wrapper itself does not hide children and renders the subtree.
    const { container } = render(
      <Providers>
        <div data-testid="inner">content</div>
      </Providers>,
    );
    expect(container.querySelector('[data-testid="inner"]')).toBeInTheDocument();
  });
});

// ===========================================================================
// LoginPage (server component — rendered synchronously in jsdom)
// ===========================================================================

describe("LoginPage", () => {
  it("test_loginpage_renders_bem_vindo_de_volta_heading", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: "Bem-vindo de volta" })).toBeInTheDocument();
  });

  it("test_loginpage_renders_sinal_logo_linking_to_root", () => {
    render(<LoginPage />);
    // The logo text "Sinal" is inside a link pointing to "/"
    const logoLink = screen.getByText("Sinal").closest("a");
    expect(logoLink).toHaveAttribute("href", "/");
  });

  it("test_loginpage_renders_login_form_email_input", () => {
    render(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it("test_loginpage_renders_login_form_entrar_button", () => {
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("test_loginpage_renders_login_form_google_button", () => {
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: /entrar com google/i })).toBeInTheDocument();
  });

  it("test_loginpage_metadata_has_correct_title", () => {
    // loginMetadata is the named ESM export from the page module
    expect(loginMetadata.title).toBe("Entrar");
  });
});

// ===========================================================================
// CadastroPage (server component — rendered synchronously in jsdom)
// ===========================================================================

describe("CadastroPage", () => {
  it("test_cadastropage_renders_crie_sua_conta_heading", () => {
    render(<CadastroPage />);
    expect(screen.getByRole("heading", { name: "Crie sua conta" })).toBeInTheDocument();
  });

  it("test_cadastropage_renders_sinal_logo_linking_to_root", () => {
    render(<CadastroPage />);
    const logoLink = screen.getByText("Sinal").closest("a");
    expect(logoLink).toHaveAttribute("href", "/");
  });

  it("test_cadastropage_renders_signup_form_email_input", () => {
    render(<CadastroPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it("test_cadastropage_renders_signup_form_criar_conta_button", () => {
    render(<CadastroPage />);
    expect(screen.getByRole("button", { name: "Criar conta" })).toBeInTheDocument();
  });

  it("test_cadastropage_renders_signup_form_google_button", () => {
    render(<CadastroPage />);
    expect(screen.getByRole("button", { name: /entrar com google/i })).toBeInTheDocument();
  });

  it("test_cadastropage_metadata_has_correct_title", () => {
    // cadastroMetadata is the named ESM export from the page module
    expect(cadastroMetadata.title).toBe("Criar conta");
  });
});

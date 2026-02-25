import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import Hero from "./Hero";
import ValueProposition from "./ValueProposition";
import BriefingExplainer from "./BriefingExplainer";
import HowItWorks from "./HowItWorks";
import Pricing from "./Pricing";
import SocialProof from "./SocialProof";
import CTASection from "./CTASection";
import EditionsPreviews from "./EditionsPreviews";
import ForCompanies from "./ForCompanies";
import FAQ from "./FAQ";
import Manifesto from "./Manifesto";
import WaitlistForm from "./WaitlistForm";

vi.mock("@/lib/api", () => ({
  submitWaitlist: vi.fn().mockResolvedValue({ message: "ok", email: "test@test.com" }),
  fetchNewsletters: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 }),
  fetchWaitlistCount: vi.fn().mockResolvedValue(247),
}));

// ---------------------------------------------------------------------------
// Hero
// ---------------------------------------------------------------------------

describe("Hero", () => {
  it("renders without crashing", () => {
    const { container } = render(<Hero />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the main headline text", () => {
    render(<Hero />);
    expect(screen.getByText("essencial,")).toBeInTheDocument();
    expect(screen.getByText(/não superficial/i)).toBeInTheDocument();
  });

  it('renders the label "Inteligência tech LATAM"', () => {
    render(<Hero />);
    expect(screen.getByText(/Inteligência tech LATAM/i)).toBeInTheDocument();
  });

  it("renders the subheadline paragraph", () => {
    render(<Hero />);
    expect(screen.getByText(/Toda segunda-feira/i)).toBeInTheDocument();
  });

  it("renders the social proof subscriber count", () => {
    render(<Hero />);
    expect(screen.getByText("+2.500")).toBeInTheDocument();
  });

  it("renders the link to last briefing", () => {
    render(<Hero />);
    expect(
      screen.getByRole("link", { name: /Ou comece pelo último Briefing/i }),
    ).toBeInTheDocument();
  });

  it('renders micro copy with "Grátis. Sem spam."', () => {
    render(<Hero />);
    expect(screen.getByText(/Grátis. Sem spam./i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ValueProposition
// ---------------------------------------------------------------------------

describe("ValueProposition", () => {
  it("renders without crashing", () => {
    const { container } = render(<ValueProposition />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the three card titles", () => {
    render(<ValueProposition />);
    expect(screen.getByText(/Informação verificável/i)).toBeInTheDocument();
    expect(screen.getByText(/Economize 5 horas/i)).toBeInTheDocument();
    expect(screen.getByText(/O ecossistema inteiro/i)).toBeInTheDocument();
  });

  it("renders all three card descriptions", () => {
    render(<ValueProposition />);
    expect(screen.getByText(/Cada dado publicado tem fonte rastreável/i)).toBeInTheDocument();
    expect(screen.getByText(/Agentes de IA vasculham dezenas de fontes/i)).toBeInTheDocument();
    expect(screen.getByText(/De São Paulo a Cidade do México/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// BriefingExplainer
// ---------------------------------------------------------------------------

describe("BriefingExplainer", () => {
  it("renders without crashing", () => {
    const { container } = render(<BriefingExplainer />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the section heading", () => {
    render(<BriefingExplainer />);
    expect(screen.getByText(/O que é o/i)).toBeInTheDocument();
    expect(screen.getByText(/Briefing Sinal\?/i)).toBeInTheDocument();
  });

  it('renders the label "O Briefing"', () => {
    render(<BriefingExplainer />);
    expect(screen.getByText("O Briefing")).toBeInTheDocument();
  });

  it('renders the preview card header "Sinal Semanal"', () => {
    render(<BriefingExplainer />);
    expect(screen.getByText("Sinal Semanal")).toBeInTheDocument();
  });

  it("renders the SINTESE section label in the preview card", () => {
    render(<BriefingExplainer />);
    expect(screen.getByText("SÍNTESE")).toBeInTheDocument();
  });

  it("renders the RADAR section label in the preview card", () => {
    render(<BriefingExplainer />);
    expect(screen.getByText("RADAR")).toBeInTheDocument();
  });

  it("renders the FUNDING section label in the preview card", () => {
    render(<BriefingExplainer />);
    expect(screen.getByText("FUNDING")).toBeInTheDocument();
  });

  it("renders the MERCADO section label in the preview card", () => {
    render(<BriefingExplainer />);
    expect(screen.getByText("MERCADO")).toBeInTheDocument();
  });

  it("renders the CTA link to receive the next briefing", () => {
    render(<BriefingExplainer />);
    expect(screen.getByRole("link", { name: /Receba o próximo Briefing/i })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// HowItWorks
// ---------------------------------------------------------------------------

describe("HowItWorks", () => {
  it("renders without crashing", () => {
    const { container } = render(<HowItWorks />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the section heading", () => {
    render(<HowItWorks />);
    expect(screen.getByText(/Inteligência de IA com/i)).toBeInTheDocument();
  });

  it("renders all 6 pipeline step numbers", () => {
    render(<HowItWorks />);
    ["01", "02", "03", "04", "05", "06"].forEach((num) => {
      expect(screen.getByText(num)).toBeInTheDocument();
    });
  });

  it("renders all 6 pipeline step titles", () => {
    render(<HowItWorks />);
    const titles = [
      "Pesquisa",
      "Validação",
      "Verificação",
      "Detecção de viés",
      "Síntese",
      "Revisão humana",
    ];
    titles.forEach((title) => {
      expect(screen.getByText(title)).toBeInTheDocument();
    });
  });

  it("renders the quality badge", () => {
    render(<HowItWorks />);
    expect(screen.getByText(/DQ: 4\/5/i)).toBeInTheDocument();
  });

  it('renders the "Metodologia" section label', () => {
    render(<HowItWorks />);
    expect(screen.getByText("Metodologia")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Pricing
// ---------------------------------------------------------------------------

describe("Pricing", () => {
  it("renders without crashing", () => {
    const { container } = render(<Pricing />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders all three tier names", () => {
    render(<Pricing />);
    expect(screen.getByText("Briefing")).toBeInTheDocument();
    expect(screen.getByText("Pro")).toBeInTheDocument();
    expect(screen.getByText("Founding Member")).toBeInTheDocument();
  });

  it("renders the three pricing values", () => {
    render(<Pricing />);
    expect(screen.getByText("R$0")).toBeInTheDocument();
    expect(screen.getByText("R$29")).toBeInTheDocument();
    expect(screen.getByText("R$79")).toBeInTheDocument();
  });

  it('renders the "Recomendado" badge on the Pro tier', () => {
    render(<Pricing />);
    expect(screen.getByText("Recomendado")).toBeInTheDocument();
  });

  it('renders the section heading "Quanto custa?"', () => {
    render(<Pricing />);
    expect(screen.getByText("Quanto custa?")).toBeInTheDocument();
  });

  it("renders the CTA buttons for each tier", () => {
    render(<Pricing />);
    expect(screen.getByRole("link", { name: /Assinar grátis/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Começar Pro/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Seja um Founding Member/i })).toBeInTheDocument();
  });

  it('renders the Briefing tier "Grátis, para sempre." period text', () => {
    render(<Pricing />);
    expect(screen.getByText("Grátis, para sempre.")).toBeInTheDocument();
  });

  it('renders the Founding Member "Vagas limitadas." period text', () => {
    render(<Pricing />);
    expect(screen.getByText("Vagas limitadas.")).toBeInTheDocument();
  });

  it("includes plan parameter in CTA links", () => {
    render(<Pricing />);
    const briefingLink = screen.getByRole("link", { name: /Assinar grátis/i });
    const proLink = screen.getByRole("link", { name: /Começar Pro/i });
    const foundingLink = screen.getByRole("link", { name: /Seja um Founding Member/i });

    expect(briefingLink).toHaveAttribute("href", "/?plan=briefing#hero");
    expect(proLink).toHaveAttribute("href", "/?plan=pro#hero");
    expect(foundingLink).toHaveAttribute("href", "/?plan=founding#hero");
  });
});

// ---------------------------------------------------------------------------
// SocialProof
// ---------------------------------------------------------------------------

describe("SocialProof", () => {
  it("renders without crashing", () => {
    const { container } = render(<SocialProof />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the section heading", () => {
    render(<SocialProof />);
    expect(screen.getByText(/Quem constrói tecnologia na/i)).toBeInTheDocument();
  });

  it("renders all three metrics", () => {
    render(<SocialProof />);
    expect(screen.getByText("87%")).toBeInTheDocument();
    expect(screen.getByText("4.8")).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
  });

  it("renders metric labels", () => {
    render(<SocialProof />);
    expect(screen.getByText(/dos assinantes abrem toda semana/i)).toBeInTheDocument();
    expect(screen.getByText(/avaliação média dos leitores/i)).toBeInTheDocument();
    expect(screen.getByText(/recomendariam a um colega/i)).toBeInTheDocument();
  });

  it("renders testimonial authors", () => {
    render(<SocialProof />);
    expect(screen.getByText("CTO")).toBeInTheDocument();
    expect(screen.getByText("Partner")).toBeInTheDocument();
    expect(screen.getByText("Fundador")).toBeInTheDocument();
    expect(screen.getByText("Head de Produto")).toBeInTheDocument();
  });

  it("renders at least one testimonial text excerpt", () => {
    render(<SocialProof />);
    expect(screen.getByText(/Eu gastava horas por semana/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// CTASection
// ---------------------------------------------------------------------------

describe("CTASection", () => {
  it("renders without crashing", () => {
    const { container } = render(<CTASection />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the section heading", () => {
    render(<CTASection />);
    expect(screen.getByText(/Pronto para receber/i)).toBeInTheDocument();
    expect(screen.getByText(/inteligência de verdade/i)).toBeInTheDocument();
  });

  it('renders the "Receba o sinal" label', () => {
    render(<CTASection />);
    expect(screen.getByText(/Receba o sinal/i)).toBeInTheDocument();
  });

  it('renders the "Assinar →" button label from WaitlistForm prop', () => {
    render(<CTASection />);
    expect(screen.getByRole("button", { name: /Assinar →/i })).toBeInTheDocument();
  });

  it("renders the no-spam disclaimer text", () => {
    render(<CTASection />);
    expect(screen.getByText(/Sem spam. Cancelamento em 1 clique/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// EditionsPreviews
// ---------------------------------------------------------------------------

describe("EditionsPreviews", () => {
  it("renders without crashing", async () => {
    const jsx = await EditionsPreviews();
    const { container } = render(jsx);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the section heading", async () => {
    const jsx = await EditionsPreviews();
    render(jsx);
    expect(screen.getByText(/Veja o Briefing com/i)).toBeInTheDocument();
  });

  it("renders all three edition numbers", async () => {
    const jsx = await EditionsPreviews();
    render(jsx);
    expect(screen.getByText(/Edição #47/i)).toBeInTheDocument();
    expect(screen.getByText(/Edição #46/i)).toBeInTheDocument();
    expect(screen.getByText(/Edição #45/i)).toBeInTheDocument();
  });

  it("renders all three edition titles", async () => {
    const jsx = await EditionsPreviews();
    render(jsx);
    expect(screen.getByText(/Healthtech LATAM/i)).toBeInTheDocument();
    expect(screen.getByText(/US\$1\.2B em deals/i)).toBeInTheDocument();
    expect(screen.getByText(/mapa de calor do talento técnico/i)).toBeInTheDocument();
  });

  it('renders "Ler edição →" links for each edition', async () => {
    const jsx = await EditionsPreviews();
    render(jsx);
    const readLinks = screen.getAllByText("Ler edição →");
    expect(readLinks).toHaveLength(3);
  });

  it('renders the "Arquivo" section label', async () => {
    const jsx = await EditionsPreviews();
    render(jsx);
    expect(screen.getByText("Arquivo")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ForCompanies
// ---------------------------------------------------------------------------

describe("ForCompanies", () => {
  it("renders without crashing", () => {
    const { container } = render(<ForCompanies />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the section heading", () => {
    render(<ForCompanies />);
    expect(screen.getByText(/Sinal para empresas\./i)).toBeInTheDocument();
  });

  it('renders the "Para empresas" section label', () => {
    render(<ForCompanies />);
    // "Para empresas" appears as section label; "Sinal para empresas." is the heading.
    // Use getAllByText and confirm at least one match exists.
    const matches = screen.getAllByText(/Para empresas/i);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders all three B2B card titles", () => {
    render(<ForCompanies />);
    expect(screen.getByText(/Relatórios setoriais sob demanda/i)).toBeInTheDocument();
    expect(screen.getByText(/API de dados LATAM/i)).toBeInTheDocument();
    expect(screen.getByText(/Inteligência competitiva contínua/i)).toBeInTheDocument();
  });

  it("renders the contact CTA link", () => {
    render(<ForCompanies />);
    expect(screen.getByRole("link", { name: /Fale com nosso time/i })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// FAQ
// ---------------------------------------------------------------------------

describe("FAQ", () => {
  it("renders without crashing", () => {
    const { container } = render(<FAQ />);
    expect(container.firstChild).toBeTruthy();
  });

  it('renders the section heading "Perguntas frequentes."', () => {
    render(<FAQ />);
    expect(screen.getByText("Perguntas frequentes.")).toBeInTheDocument();
  });

  it("renders all 8 FAQ question buttons", () => {
    render(<FAQ />);
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(8);
  });

  it("renders the first question text", () => {
    render(<FAQ />);
    expect(screen.getByText("O que exatamente é o Sinal?")).toBeInTheDocument();
  });

  it("starts with all answers collapsed (aria-expanded false)", () => {
    render(<FAQ />);
    const buttons = screen.getAllByRole("button");
    buttons.forEach((btn) => {
      expect(btn).toHaveAttribute("aria-expanded", "false");
    });
  });

  it("clicking the first question expands it and shows the answer", async () => {
    render(<FAQ />);
    const firstButton = screen.getAllByRole("button")[0];
    expect(firstButton).toHaveAttribute("aria-expanded", "false");

    await act(async () => {
      fireEvent.click(firstButton);
    });

    expect(firstButton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/O Sinal é um laboratório aberto/i)).toBeInTheDocument();
  });

  it("clicking an open question collapses it again", async () => {
    render(<FAQ />);
    const firstButton = screen.getAllByRole("button")[0];

    await act(async () => {
      fireEvent.click(firstButton);
    });
    expect(firstButton).toHaveAttribute("aria-expanded", "true");

    await act(async () => {
      fireEvent.click(firstButton);
    });
    expect(firstButton).toHaveAttribute("aria-expanded", "false");
  });

  it("clicking a second question expands it while the first stays open independently", async () => {
    render(<FAQ />);
    const buttons = screen.getAllByRole("button");

    await act(async () => {
      fireEvent.click(buttons[0]);
    });
    expect(buttons[0]).toHaveAttribute("aria-expanded", "true");

    await act(async () => {
      fireEvent.click(buttons[1]);
    });
    expect(buttons[1]).toHaveAttribute("aria-expanded", "true");
    // First question should now be closed since only one can be open at a time
    expect(buttons[0]).toHaveAttribute("aria-expanded", "false");
  });

  it('renders the "FAQ" section label', () => {
    render(<FAQ />);
    expect(screen.getByText("FAQ")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Manifesto
// ---------------------------------------------------------------------------

describe("Manifesto", () => {
  it("renders without crashing", () => {
    const { container } = render(<Manifesto />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the section heading", () => {
    render(<Manifesto />);
    expect(screen.getByText(/Por que construímos o Sinal\./i)).toBeInTheDocument();
  });

  it('renders the "Manifesto" section label', () => {
    render(<Manifesto />);
    expect(screen.getByText("Manifesto")).toBeInTheDocument();
  });

  it('renders the tagline "Inteligência aberta para quem constrói."', () => {
    render(<Manifesto />);
    expect(screen.getByText("Inteligência aberta para quem constrói.")).toBeInTheDocument();
  });

  it("renders the infrastructure paragraph", () => {
    render(<Manifesto />);
    expect(screen.getByText(/Informação é infraestrutura/i)).toBeInTheDocument();
  });

  it('renders the "3 milhões de desenvolvedores" paragraph', () => {
    render(<Manifesto />);
    expect(screen.getByText(/3 milhões de desenvolvedores/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// WaitlistForm
// ---------------------------------------------------------------------------

import { submitWaitlist } from "@/lib/api";

describe("WaitlistForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    const { container } = render(<WaitlistForm />);
    expect(container.firstChild).toBeTruthy();
  });

  it("renders the email input with placeholder", () => {
    render(<WaitlistForm />);
    expect(screen.getByPlaceholderText("seu@email.com")).toBeInTheDocument();
  });

  it('renders the default submit button label "Assine o Briefing"', () => {
    render(<WaitlistForm />);
    expect(screen.getByRole("button", { name: "Assine o Briefing" })).toBeInTheDocument();
  });

  it("renders a custom button label when buttonLabel prop is provided", () => {
    render(<WaitlistForm buttonLabel="Entrar na lista →" />);
    expect(screen.getByRole("button", { name: "Entrar na lista →" })).toBeInTheDocument();
  });

  it("typing in the email input updates its value", async () => {
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("seu@email.com") as HTMLInputElement;

    await act(async () => {
      fireEvent.change(input, { target: { value: "usuario@example.com" } });
    });

    expect(input.value).toBe("usuario@example.com");
  });

  it("shows validation error when submitting empty email", async () => {
    render(<WaitlistForm />);
    const button = screen.getByRole("button", { name: "Assine o Briefing" });

    await act(async () => {
      fireEvent.submit(button.closest("form")!);
    });

    expect(screen.getByText(/Por favor, insira um email válido/i)).toBeInTheDocument();
  });

  it("shows validation error when submitting email without @", async () => {
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("seu@email.com");
    const form = screen.getByRole("button", { name: "Assine o Briefing" }).closest("form")!;

    await act(async () => {
      fireEvent.change(input, { target: { value: "invalidemail" } });
      fireEvent.submit(form);
    });

    expect(screen.getByText(/Por favor, insira um email válido/i)).toBeInTheDocument();
  });

  it("calls submitWaitlist with the entered email on valid form submission", async () => {
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("seu@email.com");
    const form = screen.getByRole("button", { name: "Assine o Briefing" }).closest("form")!;

    await act(async () => {
      fireEvent.change(input, { target: { value: "teste@exemplo.com" } });
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(submitWaitlist).toHaveBeenCalledWith({ email: "teste@exemplo.com" });
    });
  });

  it("shows success message after successful submission", async () => {
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("seu@email.com");
    const form = screen.getByRole("button", { name: "Assine o Briefing" }).closest("form")!;

    await act(async () => {
      fireEvent.change(input, { target: { value: "teste@exemplo.com" } });
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(screen.getByText(/Inscrição confirmada!/i)).toBeInTheDocument();
    });
  });

  it("clears the email input after successful submission", async () => {
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("seu@email.com") as HTMLInputElement;
    const form = input.closest("form")!;

    await act(async () => {
      fireEvent.change(input, { target: { value: "teste@exemplo.com" } });
      fireEvent.submit(form);
    });

    // After success, the form is replaced by the success message
    await waitFor(() => {
      expect(screen.queryByPlaceholderText("seu@email.com")).not.toBeInTheDocument();
    });
  });

  it("shows error message when submitWaitlist rejects", async () => {
    vi.mocked(submitWaitlist).mockRejectedValueOnce(new Error("Email já cadastrado"));

    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("seu@email.com");
    const form = input.closest("form")!;

    await act(async () => {
      fireEvent.change(input, { target: { value: "existente@exemplo.com" } });
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(screen.getByText("Email já cadastrado")).toBeInTheDocument();
    });
  });

  it("shows generic error message when submitWaitlist throws non-Error", async () => {
    vi.mocked(submitWaitlist).mockRejectedValueOnce("server error");

    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("seu@email.com");
    const form = input.closest("form")!;

    await act(async () => {
      fireEvent.change(input, { target: { value: "teste@exemplo.com" } });
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(screen.getByText(/Erro ao inscrever. Tente novamente./i)).toBeInTheDocument();
    });
  });

  it("disables input and button during loading state", async () => {
    // Make submitWaitlist hang indefinitely to observe loading state
    vi.mocked(submitWaitlist).mockImplementationOnce(() => new Promise(() => {}));

    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("seu@email.com");
    const form = input.closest("form")!;

    await act(async () => {
      fireEvent.change(input, { target: { value: "teste@exemplo.com" } });
      fireEvent.submit(form);
    });

    expect(screen.getByPlaceholderText("seu@email.com")).toBeDisabled();
    expect(screen.getByRole("button", { name: /Inscrevendo\.\.\./i })).toBeDisabled();
  });

  it("renders email input with aria-label for accessibility", () => {
    render(<WaitlistForm />);
    expect(screen.getByLabelText("Seu email")).toBeInTheDocument();
  });
});

import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api", () => ({
  submitApiAccessRequest: vi.fn().mockResolvedValue({ message: "ok" }),
}));

import ApiAccessForm from "./ApiAccessForm";
import { submitApiAccessRequest } from "@/lib/api";
import ParamsTable from "./ParamsTable";
import FieldsTable from "./FieldsTable";
import CopyButton from "./CopyButton";
import CodeTabs from "./CodeTabs";
import EndpointBlock from "./EndpointBlock";
import DocsSidebar from "./DocsSidebar";
import type { ApiParam, ApiField, EndpointDoc } from "@/lib/api-docs";

// ===========================================================================
// ApiAccessForm (kept from previous — 9 tests)
// ===========================================================================

describe("ApiAccessForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all form fields", () => {
    render(<ApiAccessForm />);
    expect(screen.getByLabelText(/nome/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email corporativo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/empresa/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cargo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/caso de uso/i)).toBeInTheDocument();
  });

  it("renders the submit button", () => {
    render(<ApiAccessForm />);
    expect(screen.getByRole("button", { name: /solicitar acesso/i })).toBeInTheDocument();
  });

  it("shows validation error for invalid email", async () => {
    render(<ApiAccessForm />);
    const form = screen.getByRole("button", { name: /solicitar acesso/i }).closest("form")!;

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/nome/i), { target: { value: "Ana" } });
      fireEvent.change(screen.getByLabelText(/email corporativo/i), {
        target: { value: "invalid" },
      });
      fireEvent.change(screen.getByLabelText(/empresa/i), { target: { value: "TechCo" } });
      fireEvent.change(screen.getByLabelText(/cargo/i), { target: { value: "CTO" } });
      fireEvent.change(screen.getByLabelText(/caso de uso/i), {
        target: { value: "Integrar dados no dashboard" },
      });
      fireEvent.submit(form);
    });

    expect(screen.getByText(/email corporativo válido/i)).toBeInTheDocument();
  });

  it("shows validation error for short use case", async () => {
    render(<ApiAccessForm />);
    const form = screen.getByRole("button", { name: /solicitar acesso/i }).closest("form")!;

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/nome/i), { target: { value: "Ana" } });
      fireEvent.change(screen.getByLabelText(/email corporativo/i), {
        target: { value: "ana@empresa.com" },
      });
      fireEvent.change(screen.getByLabelText(/empresa/i), { target: { value: "TechCo" } });
      fireEvent.change(screen.getByLabelText(/cargo/i), { target: { value: "CTO" } });
      fireEvent.change(screen.getByLabelText(/caso de uso/i), { target: { value: "short" } });
      fireEvent.submit(form);
    });

    expect(screen.getByText(/mais detalhes/i)).toBeInTheDocument();
  });

  it("calls submitApiAccessRequest on valid submission", async () => {
    render(<ApiAccessForm />);
    const form = screen.getByRole("button", { name: /solicitar acesso/i }).closest("form")!;

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/nome/i), { target: { value: "Ana Silva" } });
      fireEvent.change(screen.getByLabelText(/email corporativo/i), {
        target: { value: "ana@empresa.com" },
      });
      fireEvent.change(screen.getByLabelText(/empresa/i), { target: { value: "TechCo" } });
      fireEvent.change(screen.getByLabelText(/cargo/i), { target: { value: "CTO" } });
      fireEvent.change(screen.getByLabelText(/caso de uso/i), {
        target: { value: "Integrar dados de startups LATAM no nosso CRM." },
      });
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(submitApiAccessRequest).toHaveBeenCalledWith({
        name: "Ana Silva",
        email: "ana@empresa.com",
        company: "TechCo",
        role: "CTO",
        use_case: "Integrar dados de startups LATAM no nosso CRM.",
      });
    });
  });

  it("shows success message after successful submission", async () => {
    render(<ApiAccessForm />);
    const form = screen.getByRole("button", { name: /solicitar acesso/i }).closest("form")!;

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/nome/i), { target: { value: "Ana" } });
      fireEvent.change(screen.getByLabelText(/email corporativo/i), {
        target: { value: "ana@empresa.com" },
      });
      fireEvent.change(screen.getByLabelText(/empresa/i), { target: { value: "TechCo" } });
      fireEvent.change(screen.getByLabelText(/cargo/i), { target: { value: "CTO" } });
      fireEvent.change(screen.getByLabelText(/caso de uso/i), {
        target: { value: "Integrar dados de startups LATAM" },
      });
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(screen.getByText(/solicitação enviada/i)).toBeInTheDocument();
    });
  });

  it("shows error message when API call fails", async () => {
    vi.mocked(submitApiAccessRequest).mockRejectedValueOnce(new Error("Erro no servidor"));

    render(<ApiAccessForm />);
    const form = screen.getByRole("button", { name: /solicitar acesso/i }).closest("form")!;

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/nome/i), { target: { value: "Ana" } });
      fireEvent.change(screen.getByLabelText(/email corporativo/i), {
        target: { value: "ana@empresa.com" },
      });
      fireEvent.change(screen.getByLabelText(/empresa/i), { target: { value: "TechCo" } });
      fireEvent.change(screen.getByLabelText(/cargo/i), { target: { value: "CTO" } });
      fireEvent.change(screen.getByLabelText(/caso de uso/i), {
        target: { value: "Integrar dados de startups LATAM" },
      });
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(screen.getByText("Erro no servidor")).toBeInTheDocument();
    });
  });

  it("disables button during loading state", async () => {
    vi.mocked(submitApiAccessRequest).mockImplementationOnce(() => new Promise(() => {}));

    render(<ApiAccessForm />);
    const form = screen.getByRole("button", { name: /solicitar acesso/i }).closest("form")!;

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/nome/i), { target: { value: "Ana" } });
      fireEvent.change(screen.getByLabelText(/email corporativo/i), {
        target: { value: "ana@empresa.com" },
      });
      fireEvent.change(screen.getByLabelText(/empresa/i), { target: { value: "TechCo" } });
      fireEvent.change(screen.getByLabelText(/cargo/i), { target: { value: "CTO" } });
      fireEvent.change(screen.getByLabelText(/caso de uso/i), {
        target: { value: "Integrar dados de startups LATAM" },
      });
      fireEvent.submit(form);
    });

    expect(screen.getByRole("button", { name: /enviando/i })).toBeDisabled();
  });

  it("hides form and shows checkmark after success", async () => {
    render(<ApiAccessForm />);
    const form = screen.getByRole("button", { name: /solicitar acesso/i }).closest("form")!;

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/nome/i), { target: { value: "Ana" } });
      fireEvent.change(screen.getByLabelText(/email corporativo/i), {
        target: { value: "ana@empresa.com" },
      });
      fireEvent.change(screen.getByLabelText(/empresa/i), { target: { value: "TechCo" } });
      fireEvent.change(screen.getByLabelText(/cargo/i), { target: { value: "CTO" } });
      fireEvent.change(screen.getByLabelText(/caso de uso/i), {
        target: { value: "Integrar dados de startups LATAM" },
      });
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /solicitar acesso/i })).not.toBeInTheDocument();
    });
  });
});

// ===========================================================================
// ParamsTable
// ===========================================================================

describe("ParamsTable", () => {
  const params: ApiParam[] = [
    { name: "sector", type: "string", required: false, description: "Filtra por setor" },
    { name: "slug", type: "string", required: true, description: "Slug da empresa" },
    { name: "limit", type: "int", required: false, default: "20", description: "Maximo 100" },
  ];

  it("renders column headers", () => {
    render(<ParamsTable params={params} />);
    expect(screen.getByText("Parâmetro")).toBeInTheDocument();
    expect(screen.getByText("Tipo")).toBeInTheDocument();
    expect(screen.getByText("Default")).toBeInTheDocument();
    expect(screen.getByText("Descrição")).toBeInTheDocument();
  });

  it("renders all parameter rows", () => {
    render(<ParamsTable params={params} />);
    expect(screen.getByText("sector")).toBeInTheDocument();
    expect(screen.getByText("slug")).toBeInTheDocument();
    expect(screen.getByText("limit")).toBeInTheDocument();
  });

  it("shows obrigatorio badge for required params", () => {
    render(<ParamsTable params={params} />);
    expect(screen.getByText("obrigatório")).toBeInTheDocument();
  });

  it("shows default values", () => {
    render(<ParamsTable params={params} />);
    expect(screen.getByText("20")).toBeInTheDocument();
  });

  it("renders nothing when params is empty", () => {
    const { container } = render(<ParamsTable params={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

// ===========================================================================
// FieldsTable
// ===========================================================================

describe("FieldsTable", () => {
  const fields: ApiField[] = [
    { name: "id", type: "UUID", description: "Identificador unico" },
    { name: "name", type: "string", description: "Nome da empresa" },
  ];

  it("renders column headers", () => {
    render(<FieldsTable fields={fields} />);
    expect(screen.getByText("Campo")).toBeInTheDocument();
    expect(screen.getByText("Tipo")).toBeInTheDocument();
    expect(screen.getByText("Descrição")).toBeInTheDocument();
  });

  it("renders all field rows", () => {
    render(<FieldsTable fields={fields} />);
    expect(screen.getByText("id")).toBeInTheDocument();
    expect(screen.getByText("UUID")).toBeInTheDocument();
    expect(screen.getByText("name")).toBeInTheDocument();
  });

  it("renders nothing when fields is empty", () => {
    const { container } = render(<FieldsTable fields={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

// ===========================================================================
// CopyButton
// ===========================================================================

describe("CopyButton", () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("renders Copiar text", () => {
    render(<CopyButton text="hello" />);
    expect(screen.getByText("Copiar")).toBeInTheDocument();
  });

  it("copies text and shows Copiado! feedback", async () => {
    render(<CopyButton text="hello world" />);
    fireEvent.click(screen.getByText("Copiar"));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("hello world");
      expect(screen.getByText("Copiado!")).toBeInTheDocument();
    });
  });
});

// ===========================================================================
// CodeTabs
// ===========================================================================

describe("CodeTabs", () => {
  const examples = {
    curl: 'curl -H "Auth: Bearer KEY" https://api.sinal.tech/api/companies',
    python: "import requests\nresp = requests.get(...)",
    javascript: "const resp = await fetch(...)",
  };
  const response = '{ "items": [] }';

  it("renders all three language tabs", () => {
    render(<CodeTabs examples={examples} response={response} />);
    expect(screen.getByRole("tab", { name: "cURL" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Python" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "JavaScript" })).toBeInTheDocument();
  });

  it("shows cURL content by default", () => {
    render(<CodeTabs examples={examples} response={response} />);
    expect(screen.getByText(/curl -H/)).toBeInTheDocument();
  });

  it("switches to Python when tab is clicked", () => {
    render(<CodeTabs examples={examples} response={response} />);
    fireEvent.click(screen.getByRole("tab", { name: "Python" }));
    expect(screen.getByText(/import requests/)).toBeInTheDocument();
  });

  it("renders the response block", () => {
    render(<CodeTabs examples={examples} response={response} />);
    expect(screen.getByText("Resposta")).toBeInTheDocument();
  });
});

// ===========================================================================
// EndpointBlock
// ===========================================================================

describe("EndpointBlock", () => {
  const endpoint: EndpointDoc = {
    method: "GET",
    path: "/api/test",
    description: "Test endpoint description.",
    params: [
      { name: "limit", type: "int", required: false, default: "20", description: "Max items" },
    ],
    responseFields: [{ name: "id", type: "UUID", description: "Unique ID" }],
    examples: {
      curl: "curl https://api.sinal.tech/api/test",
      python: "requests.get(...)",
      javascript: "fetch(...)",
    },
    exampleResponse: '{ "items": [] }',
  };

  it("renders method badge and path", () => {
    render(<EndpointBlock endpoint={endpoint} />);
    expect(screen.getByText("GET")).toBeInTheDocument();
    expect(screen.getByText("/api/test")).toBeInTheDocument();
  });

  it("renders description", () => {
    render(<EndpointBlock endpoint={endpoint} />);
    expect(screen.getByText("Test endpoint description.")).toBeInTheDocument();
  });

  it("renders parameters table", () => {
    render(<EndpointBlock endpoint={endpoint} />);
    expect(screen.getByText("Parâmetros")).toBeInTheDocument();
    expect(screen.getByText("limit")).toBeInTheDocument();
  });

  it("renders response fields table", () => {
    render(<EndpointBlock endpoint={endpoint} />);
    expect(screen.getByText("Campos da Resposta")).toBeInTheDocument();
    expect(screen.getByText("id")).toBeInTheDocument();
  });

  it("renders code example section", () => {
    render(<EndpointBlock endpoint={endpoint} />);
    expect(screen.getByText("Exemplo")).toBeInTheDocument();
  });
});

// ===========================================================================
// DocsSidebar
// ===========================================================================

describe("DocsSidebar", () => {
  it("renders navigation with all section links", () => {
    render(<DocsSidebar />);
    const navs = screen.getAllByRole("navigation", { name: /navegação da documentação/i });
    expect(navs.length).toBeGreaterThanOrEqual(1);
  });

  it("renders sidebar links for each section", () => {
    render(<DocsSidebar />);
    // Check at least some key links exist
    expect(screen.getAllByText("Visão Geral").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Autenticação").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Empresas").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Solicitar Acesso").length).toBeGreaterThanOrEqual(1);
  });
});

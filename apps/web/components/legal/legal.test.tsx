import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import LegalSection from "./LegalSection";
import LegalTable from "./LegalTable";
import LegalPageLayout from "./LegalPageLayout";

// ---------------------------------------------------------------------------
// LegalSection
// ---------------------------------------------------------------------------

describe("LegalSection", () => {
  it("test_legal_section_renders_title", () => {
    render(
      <LegalSection id="s1" num="1" title="Definições">
        <p>Content</p>
      </LegalSection>,
    );
    expect(screen.getByText("Definições")).toBeInTheDocument();
  });

  it("test_legal_section_renders_section_number", () => {
    render(
      <LegalSection id="s1" num="1" title="Definições">
        <p>Content</p>
      </LegalSection>,
    );
    expect(screen.getByText("1.")).toBeInTheDocument();
  });

  it("test_legal_section_renders_children", () => {
    render(
      <LegalSection id="s1" num="1" title="Definições">
        <p>Some legal text here</p>
      </LegalSection>,
    );
    expect(screen.getByText("Some legal text here")).toBeInTheDocument();
  });

  it("test_legal_section_has_correct_id", () => {
    const { container } = render(
      <LegalSection id="s3" num="3" title="Cadastro">
        <p>Content</p>
      </LegalSection>,
    );
    const section = container.querySelector("section");
    expect(section).toHaveAttribute("id", "s3");
  });

  it("test_legal_section_has_scroll_margin_class", () => {
    const { container } = render(
      <LegalSection id="s1" num="1" title="Test">
        <p>Content</p>
      </LegalSection>,
    );
    const section = container.querySelector("section");
    expect(section).toHaveClass("scroll-mt-[100px]");
  });

  it("test_legal_section_renders_h2_heading", () => {
    render(
      <LegalSection id="s1" num="1" title="Definições">
        <p>Content</p>
      </LegalSection>,
    );
    expect(screen.getByRole("heading", { level: 2, name: /Definições/ })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// LegalTable
// ---------------------------------------------------------------------------

describe("LegalTable", () => {
  const headers = ["Dado", "Quando", "Obrigatório"];
  const rows = [
    ["Email", "Cadastro", "Sim"],
    ["Nome", "Opcional", "Não"],
  ];

  it("test_legal_table_renders_all_headers", () => {
    render(<LegalTable headers={headers} rows={rows} />);
    headers.forEach((h) => {
      expect(screen.getByText(h)).toBeInTheDocument();
    });
  });

  it("test_legal_table_renders_all_row_cells", () => {
    render(<LegalTable headers={headers} rows={rows} />);
    expect(screen.getByText("Email")).toBeInTheDocument();
    expect(screen.getByText("Cadastro")).toBeInTheDocument();
    expect(screen.getByText("Sim")).toBeInTheDocument();
    expect(screen.getByText("Nome")).toBeInTheDocument();
    expect(screen.getByText("Opcional")).toBeInTheDocument();
    expect(screen.getByText("Não")).toBeInTheDocument();
  });

  it("test_legal_table_renders_correct_number_of_rows", () => {
    const { container } = render(<LegalTable headers={headers} rows={rows} />);
    const tbodyRows = container.querySelectorAll("tbody tr");
    expect(tbodyRows).toHaveLength(2);
  });

  it("test_legal_table_renders_correct_number_of_header_cells", () => {
    const { container } = render(<LegalTable headers={headers} rows={rows} />);
    const ths = container.querySelectorAll("th");
    expect(ths).toHaveLength(3);
  });

  it("test_legal_table_renders_table_element", () => {
    const { container } = render(<LegalTable headers={headers} rows={rows} />);
    expect(container.querySelector("table")).toBeInTheDocument();
  });

  it("test_legal_table_handles_empty_rows", () => {
    const { container } = render(<LegalTable headers={headers} rows={[]} />);
    const tbodyRows = container.querySelectorAll("tbody tr");
    expect(tbodyRows).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// LegalPageLayout
// ---------------------------------------------------------------------------

describe("LegalPageLayout", () => {
  const defaultProps = {
    toc: ["Controlador", "Dados", "Cookies"],
    sectionPrefix: "p",
    footerLinks: [
      { label: "Termos de Uso", href: "/termos", color: "#E8FF59" },
      { label: "Contato", href: "/contato" },
    ],
  };

  // Mock IntersectionObserver
  let observeMock: ReturnType<typeof vi.fn>;
  let disconnectMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    observeMock = vi.fn();
    disconnectMock = vi.fn();
    vi.stubGlobal(
      "IntersectionObserver",
      vi.fn(() => ({
        observe: observeMock,
        disconnect: disconnectMock,
        unobserve: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("test_legal_layout_renders_children", () => {
    render(
      <LegalPageLayout {...defaultProps}>
        <p>Page content</p>
      </LegalPageLayout>,
    );
    expect(screen.getByText("Page content")).toBeInTheDocument();
  });

  it("test_legal_layout_renders_toc_items_on_desktop", () => {
    render(
      <LegalPageLayout {...defaultProps}>
        <p>Content</p>
      </LegalPageLayout>,
    );
    // Desktop sidebar renders items as separate spans; mobile renders as "1. Controlador"
    // Use regex to match both formats
    expect(screen.getAllByText(/Controlador/)).toHaveLength(2);
    expect(screen.getAllByText(/Dados/)).toHaveLength(2);
    expect(screen.getAllByText(/Cookies/)).toHaveLength(2);
  });

  it("test_legal_layout_renders_toc_numbering", () => {
    render(
      <LegalPageLayout {...defaultProps}>
        <p>Content</p>
      </LegalPageLayout>,
    );
    // Desktop has "1." as separate span; mobile has "1. Controlador" combined
    // The desktop span with exact "1." text exists
    expect(screen.getByText("1.")).toBeInTheDocument();
    expect(screen.getByText("2.")).toBeInTheDocument();
    expect(screen.getByText("3.")).toBeInTheDocument();
  });

  it("test_legal_layout_renders_footer_links", () => {
    render(
      <LegalPageLayout {...defaultProps}>
        <p>Content</p>
      </LegalPageLayout>,
    );
    const termosLinks = screen.getAllByText(/Termos de Uso/);
    expect(termosLinks.length).toBeGreaterThanOrEqual(1);
  });

  it("test_legal_layout_footer_link_has_correct_href", () => {
    render(
      <LegalPageLayout {...defaultProps}>
        <p>Content</p>
      </LegalPageLayout>,
    );
    const termosLink = screen.getAllByText(/Termos de Uso/)[0].closest("a");
    expect(termosLink).toHaveAttribute("href", "/termos");
  });

  it("test_legal_layout_toc_links_have_correct_href", () => {
    render(
      <LegalPageLayout {...defaultProps}>
        <p>Content</p>
      </LegalPageLayout>,
    );
    // Desktop TOC links point to #p1, #p2, #p3
    const controladorLinks = screen.getAllByText("Controlador");
    const firstLink = controladorLinks[0].closest("a");
    expect(firstLink).toHaveAttribute("href", "#p1");
  });

  it("test_legal_layout_sets_up_intersection_observer", () => {
    render(
      <LegalPageLayout {...defaultProps}>
        <p>Content</p>
      </LegalPageLayout>,
    );
    expect(IntersectionObserver).toHaveBeenCalledTimes(1);
  });

  it("test_legal_layout_disconnects_observer_on_unmount", () => {
    const { unmount } = render(
      <LegalPageLayout {...defaultProps}>
        <p>Content</p>
      </LegalPageLayout>,
    );
    unmount();
    expect(disconnectMock).toHaveBeenCalledTimes(1);
  });

  it("test_legal_layout_renders_indice_label", () => {
    render(
      <LegalPageLayout {...defaultProps}>
        <p>Content</p>
      </LegalPageLayout>,
    );
    expect(screen.getAllByText("ÍNDICE")).toHaveLength(2); // desktop + mobile
  });
});

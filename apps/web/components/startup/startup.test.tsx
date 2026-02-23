import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { Company } from "@/lib/company";
import { SECTOR_OPTIONS } from "@/lib/company";
import { companyJsonLd } from "@/lib/jsonld";

import CompanyCard from "@/components/startup/CompanyCard";
import CompanyDetail from "@/components/startup/CompanyDetail";
import SectorFilter from "@/components/startup/SectorFilter";

// ---------------------------------------------------------------------------
// Shared test fixtures
// ---------------------------------------------------------------------------

const fullCompany: Company = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  name: "Nubank",
  slug: "nubank",
  description: "Digital bank revolutionizing financial services in Latin America",
  short_description: "Leading digital bank in Brazil",
  sector: "Fintech",
  sub_sector: "Digital Banking",
  city: "São Paulo",
  state: "SP",
  country: "Brazil",
  tags: ["fintech", "banking", "unicorn", "payments"],
  tech_stack: ["Python", "Clojure", "Kafka"],
  founded_date: "2013-05-06",
  team_size: 8000,
  business_model: "B2C",
  website: "https://nubank.com.br",
  github_url: "https://github.com/nubank",
  linkedin_url: "https://linkedin.com/company/nubank",
  twitter_url: "https://twitter.com/nubank",
  source_count: 5,
  status: "active",
  created_at: "2026-02-10T10:00:00Z",
};

const minimalCompany: Company = {
  id: "550e8400-e29b-41d4-a716-446655440001",
  name: "Stealth Startup",
  slug: "stealth-startup",
  description: null,
  short_description: null,
  sector: null,
  sub_sector: null,
  city: null,
  state: null,
  country: "Brazil",
  tags: null,
  tech_stack: null,
  founded_date: null,
  team_size: null,
  business_model: null,
  website: null,
  github_url: null,
  linkedin_url: null,
  twitter_url: null,
  source_count: 1,
  status: "active",
  created_at: "2026-02-10T10:00:00Z",
};

// ---------------------------------------------------------------------------
// CompanyCard
// ---------------------------------------------------------------------------

describe("CompanyCard", () => {
  it("test_companycard_render_shows_company_name", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("Nubank")).toBeInTheDocument();
  });

  it("test_companycard_render_shows_short_description", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("Leading digital bank in Brazil")).toBeInTheDocument();
  });

  it("test_companycard_render_shows_sector_badge", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("Fintech")).toBeInTheDocument();
  });

  it("test_companycard_render_shows_location", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("São Paulo, Brazil")).toBeInTheDocument();
  });

  it("test_companycard_render_links_to_detail_page", () => {
    render(<CompanyCard company={fullCompany} />);
    const link = screen.getByRole("link", { name: "Ver: Nubank" });
    expect(link).toHaveAttribute("href", "/startup/nubank");
  });

  it("test_companycard_render_shows_tags_max_three", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("fintech")).toBeInTheDocument();
    expect(screen.getByText("banking")).toBeInTheDocument();
    expect(screen.getByText("unicorn")).toBeInTheDocument();
    // 4th tag should be hidden, showing "+1" instead
    expect(screen.queryByText("payments")).not.toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
  });

  it("test_companycard_render_shows_source_count_when_multiple", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("5 fontes")).toBeInTheDocument();
  });

  it("test_companycard_render_hides_source_count_when_single", () => {
    render(<CompanyCard company={minimalCompany} />);
    expect(screen.queryByText(/fontes/)).not.toBeInTheDocument();
  });

  it("test_companycard_render_handles_minimal_company", () => {
    render(<CompanyCard company={minimalCompany} />);
    expect(screen.getByText("Stealth Startup")).toBeInTheDocument();
    // No sector badge
    expect(screen.queryByText("Fintech")).not.toBeInTheDocument();
    // No tags
    expect(screen.queryByText("fintech")).not.toBeInTheDocument();
  });

  it("test_companycard_render_uses_description_when_no_short_description", () => {
    const company: Company = {
      ...minimalCompany,
      description: "A long description for a startup without a short description field",
    };
    render(<CompanyCard company={company} />);
    expect(
      screen.getByText("A long description for a startup without a short description field"),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// CompanyDetail
// ---------------------------------------------------------------------------

describe("CompanyDetail", () => {
  it("test_companydetail_render_shows_company_name_heading", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByRole("heading", { name: "Nubank" })).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_sector_badge", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Fintech")).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_sub_sector", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Digital Banking")).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_location_with_state", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("São Paulo, SP, Brazil")).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_description", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(
      screen.getByText("Digital bank revolutionizing financial services in Latin America"),
    ).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_founded_date", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Fundada")).toBeInTheDocument();
    expect(screen.getByText("2013-05-06")).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_team_size", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Equipe")).toBeInTheDocument();
    expect(screen.getByText("~8000")).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_business_model", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Modelo")).toBeInTheDocument();
    expect(screen.getByText("B2C")).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_tech_stack", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Tech Stack")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("Clojure")).toBeInTheDocument();
    expect(screen.getByText("Kafka")).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_all_tags", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Tags")).toBeInTheDocument();
    expect(screen.getByText("fintech")).toBeInTheDocument();
    expect(screen.getByText("banking")).toBeInTheDocument();
    expect(screen.getByText("unicorn")).toBeInTheDocument();
    expect(screen.getByText("payments")).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_external_links", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Website")).toBeInTheDocument();
    expect(screen.getByText("GitHub")).toBeInTheDocument();
    expect(screen.getByText("LinkedIn")).toBeInTheDocument();
    expect(screen.getByText("Twitter")).toBeInTheDocument();

    const websiteLink = screen.getByText("Website").closest("a");
    expect(websiteLink).toHaveAttribute("href", "https://nubank.com.br");
    expect(websiteLink).toHaveAttribute("target", "_blank");
  });

  it("test_companydetail_render_shows_back_link", () => {
    render(<CompanyDetail company={fullCompany} />);
    const backLinks = screen.getAllByRole("link", { name: /Voltar ao Mapa/i });
    expect(backLinks.length).toBeGreaterThanOrEqual(1);
    expect(backLinks[0]).toHaveAttribute("href", "/startups");
  });

  it("test_companydetail_render_shows_source_count", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("5 fontes")).toBeInTheDocument();
  });

  it("test_companydetail_render_handles_minimal_company", () => {
    render(<CompanyDetail company={minimalCompany} />);
    expect(screen.getByRole("heading", { name: "Stealth Startup" })).toBeInTheDocument();
    // No tech stack section
    expect(screen.queryByText("Tech Stack")).not.toBeInTheDocument();
    // No tags section
    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
    // No links section
    expect(screen.queryByText("Links")).not.toBeInTheDocument();
    // No details (founded, team, model)
    expect(screen.queryByText("Fundada")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SectorFilter
// ---------------------------------------------------------------------------

describe("SectorFilter", () => {
  it("test_sectorfilter_render_shows_todos_pill", () => {
    render(<SectorFilter />);
    expect(screen.getByText("Todos")).toBeInTheDocument();
  });

  it("test_sectorfilter_render_todos_is_active_by_default", () => {
    render(<SectorFilter />);
    const todosButton = screen.getByText("Todos").closest("button");
    expect(todosButton).toHaveAttribute("aria-pressed", "true");
  });

  it("test_sectorfilter_render_shows_sector_pills", () => {
    render(<SectorFilter />);
    for (const sector of SECTOR_OPTIONS) {
      expect(screen.getByText(sector)).toBeInTheDocument();
    }
  });

  it("test_sectorfilter_click_sector_pill_does_not_crash", () => {
    render(<SectorFilter />);
    const fintechButton = screen.getByText("Fintech").closest("button")!;
    // Verify clicking doesn't throw
    expect(() => fireEvent.click(fintechButton)).not.toThrow();
  });

  it("test_sectorfilter_click_todos_does_not_crash", () => {
    render(<SectorFilter />);
    const todosButton = screen.getByText("Todos").closest("button")!;
    expect(() => fireEvent.click(todosButton)).not.toThrow();
  });

  it("test_sectorfilter_all_pills_are_buttons", () => {
    render(<SectorFilter />);
    // Todos + all sector options should be buttons
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBe(1 + SECTOR_OPTIONS.length);
  });

  it("test_sectorfilter_render_group_has_accessible_label", () => {
    render(<SectorFilter />);
    expect(screen.getByRole("group", { name: "Filtrar por setor" })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// JSON-LD helper
// ---------------------------------------------------------------------------

describe("companyJsonLd", () => {
  it("test_jsonld_full_company_includes_all_fields", () => {
    const result = companyJsonLd(fullCompany);
    expect(result).toMatchObject({
      "@context": "https://schema.org",
      "@type": "Organization",
      name: "Nubank",
      url: "https://nubank.com.br",
      foundingDate: "2013-05-06",
      address: {
        "@type": "PostalAddress",
        addressLocality: "São Paulo",
        addressRegion: "SP",
        addressCountry: "Brazil",
      },
      numberOfEmployees: {
        "@type": "QuantitativeValue",
        value: 8000,
      },
    });
  });

  it("test_jsonld_minimal_company_omits_optional_fields", () => {
    const result = companyJsonLd(minimalCompany) as Record<string, unknown>;
    expect(result["@context"]).toBe("https://schema.org");
    expect(result["@type"]).toBe("Organization");
    expect(result.name).toBe("Stealth Startup");
    expect(result.url).toBeUndefined();
    expect(result.foundingDate).toBeUndefined();
    expect(result.numberOfEmployees).toBeUndefined();
  });

  it("test_jsonld_uses_description_field", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    expect(result.description).toBe(
      "Digital bank revolutionizing financial services in Latin America",
    );
  });

  it("test_jsonld_falls_back_to_short_description", () => {
    const company: Company = { ...fullCompany, description: null };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.description).toBe("Leading digital bank in Brazil");
  });
});

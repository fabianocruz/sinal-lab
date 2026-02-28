import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { Company } from "@/lib/company";
import { SECTOR_OPTIONS, formatDomain } from "@/lib/company";
import { companyJsonLd, homepageJsonLd, articleJsonLd } from "@/lib/jsonld";

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
  funding_stage: "Series C+",
  total_funding_usd: 2_200_000_000,
  is_trending: false,
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
  funding_stage: null,
  total_funding_usd: null,
  is_trending: null,
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

  it("test_companycard_render_shows_funding_stage_in_stats", () => {
    render(<CompanyCard company={fullCompany} />);
    // When funding_stage exists, bottom bar shows stage instead of sector
    expect(screen.getByText("Series C+")).toBeInTheDocument();
    expect(screen.getByText("Stage")).toBeInTheDocument();
  });

  it("test_companycard_render_shows_sector_when_no_funding_stage", () => {
    const company: Company = { ...fullCompany, funding_stage: null };
    render(<CompanyCard company={company} />);
    expect(screen.getByText("Fintech")).toBeInTheDocument();
    expect(screen.getByText("Setor")).toBeInTheDocument();
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
    // 4th tag should be hidden (only 3 shown)
    expect(screen.queryByText("payments")).not.toBeInTheDocument();
  });

  it("test_companycard_render_shows_funding_stage", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("Series C+")).toBeInTheDocument();
  });

  it("test_companycard_render_shows_funding_amount", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("$2.2B")).toBeInTheDocument();
  });

  it("test_companycard_render_shows_team_size", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("8000")).toBeInTheDocument();
    expect(screen.getByText("Equipe")).toBeInTheDocument();
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

  it("test_companycard_render_shows_website_domain", () => {
    render(<CompanyCard company={fullCompany} />);
    expect(screen.getByText("nubank.com.br")).toBeInTheDocument();
  });

  it("test_companycard_render_hides_domain_when_no_website", () => {
    render(<CompanyCard company={minimalCompany} />);
    expect(screen.queryByText(/\.com/)).not.toBeInTheDocument();
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
    // Sector appears in breadcrumb and meta row
    const sectorElements = screen.getAllByText("Fintech");
    expect(sectorElements.length).toBeGreaterThanOrEqual(1);
  });

  it("test_companydetail_render_shows_sub_sector", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Digital Banking")).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_location", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText(/São Paulo, Brazil/)).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_description", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(
      screen.getByText("Digital bank revolutionizing financial services in Latin America"),
    ).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_founded_year", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText(/Fundada em 2013/)).toBeInTheDocument();
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
    expect(screen.getByText(/Stack Tecnológico/)).toBeInTheDocument();
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
    // Website shows cleaned domain
    expect(screen.getByText(/nubank\.com\.br/)).toBeInTheDocument();
    // LinkedIn shows "in" label
    expect(screen.getByText("in")).toBeInTheDocument();
    // GitHub shows "gh" label
    expect(screen.getByText("gh")).toBeInTheDocument();

    const websiteLink = screen.getByText(/nubank\.com\.br/).closest("a");
    expect(websiteLink).toHaveAttribute("href", "https://nubank.com.br");
    expect(websiteLink).toHaveAttribute("target", "_blank");
  });

  it("test_companydetail_render_shows_back_link", () => {
    render(<CompanyDetail company={fullCompany} />);
    const backLinks = screen.getAllByRole("link", { name: /Voltar ao Mapa/i });
    expect(backLinks.length).toBeGreaterThanOrEqual(1);
    expect(backLinks[0]).toHaveAttribute("href", "/startups");
  });

  it("test_companydetail_render_shows_source_count_in_provenance", () => {
    render(<CompanyDetail company={fullCompany} />);
    // Source count appears in stat box and provenance section
    const fontesElements = screen.getAllByText("Fontes");
    expect(fontesElements.length).toBeGreaterThanOrEqual(1);
    // "5" also appears in stat box and provenance
    const countElements = screen.getAllByText(String(fullCompany.source_count));
    expect(countElements.length).toBeGreaterThanOrEqual(1);
  });

  it("test_companydetail_render_shows_funding_stage_badge", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.getByText("Series C+")).toBeInTheDocument();
  });

  it("test_companydetail_render_handles_minimal_company", () => {
    render(<CompanyDetail company={minimalCompany} />);
    expect(screen.getByRole("heading", { name: "Stealth Startup" })).toBeInTheDocument();
    // No tech stack section
    expect(screen.queryByText(/Stack Tecnológico/)).not.toBeInTheDocument();
    // No tags section
    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
    // No founded date
    expect(screen.queryByText(/Fundada em/)).not.toBeInTheDocument();
  });

  it("test_companydetail_full_company_shows_all_dynamic_stats", () => {
    render(<CompanyDetail company={fullCompany} />);
    // Full company has: funding, team_size, source_count, business_model, founded_date
    expect(screen.getByText("Funding Total")).toBeInTheDocument();
    expect(screen.getByText("$2.2B")).toBeInTheDocument();
    expect(screen.getByText("Equipe")).toBeInTheDocument();
    expect(screen.getByText("~8000")).toBeInTheDocument();
    // "Fontes" appears in both stat box and provenance section
    const fontesElements = screen.getAllByText("Fontes");
    expect(fontesElements.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Modelo")).toBeInTheDocument();
    expect(screen.getByText("B2C")).toBeInTheDocument();
  });

  it("test_companydetail_minimal_company_shows_only_fontes_stat", () => {
    render(<CompanyDetail company={minimalCompany} />);
    // Minimal company has no funding, team_size, business_model, or founded_date
    // "Fontes" appears in both stat box and provenance section
    const fontesElements = screen.getAllByText("Fontes");
    expect(fontesElements.length).toBeGreaterThanOrEqual(1);
    // Verify no rich stats are shown
    expect(screen.queryByText("Funding Total")).not.toBeInTheDocument();
    expect(screen.queryByText("Equipe")).not.toBeInTheDocument();
    expect(screen.queryByText("Modelo")).not.toBeInTheDocument();
    expect(screen.queryByText("Fundada")).not.toBeInTheDocument();
  });

  it("test_companydetail_render_shows_placeholder_when_no_description_or_tags", () => {
    render(<CompanyDetail company={minimalCompany} />);
    expect(screen.getByText(/Perfil em construção/)).toBeInTheDocument();
    expect(screen.getByText(/Nossos agentes estão coletando/)).toBeInTheDocument();
  });

  it("test_companydetail_render_shows_github_link_in_placeholder_when_available", () => {
    const ghCompany: Company = {
      ...minimalCompany,
      github_url: "https://github.com/example-org",
    };
    render(<CompanyDetail company={ghCompany} />);
    expect(screen.getByText(/Perfil em construção/)).toBeInTheDocument();
    const ghLink = screen.getByRole("link", { name: /Ver no GitHub/ });
    expect(ghLink).toHaveAttribute("href", "https://github.com/example-org");
  });

  it("test_companydetail_render_hides_placeholder_when_description_exists", () => {
    render(<CompanyDetail company={fullCompany} />);
    expect(screen.queryByText(/Perfil em construção/)).not.toBeInTheDocument();
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
// formatDomain helper
// ---------------------------------------------------------------------------

describe("formatDomain", () => {
  it("test_formatdomain_strips_protocol_and_www", () => {
    expect(formatDomain("https://www.nubank.com.br")).toBe("nubank.com.br");
  });

  it("test_formatdomain_handles_no_www", () => {
    expect(formatDomain("https://nubank.com.br")).toBe("nubank.com.br");
  });

  it("test_formatdomain_handles_missing_protocol", () => {
    expect(formatDomain("www.lapzo.com")).toBe("lapzo.com");
  });

  it("test_formatdomain_returns_null_for_null", () => {
    expect(formatDomain(null)).toBeNull();
  });

  it("test_formatdomain_returns_null_for_invalid_url", () => {
    expect(formatDomain("not a url")).toBeNull();
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

// ---------------------------------------------------------------------------
// homepageJsonLd helper
// ---------------------------------------------------------------------------

describe("homepageJsonLd", () => {
  it("test_homepage_jsonld_returns_organization_and_website", () => {
    const result = homepageJsonLd();
    expect(result).toHaveLength(2);
    expect(result[0]).toMatchObject({
      "@context": "https://schema.org",
      "@type": "Organization",
      name: "Sinal",
    });
    expect(result[1]).toMatchObject({
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: "Sinal",
    });
  });

  it("test_homepage_jsonld_website_has_search_action", () => {
    const result = homepageJsonLd();
    const website = result[1] as Record<string, unknown>;
    expect(website.potentialAction).toBeDefined();
    const action = website.potentialAction as Record<string, unknown>;
    expect(action["@type"]).toBe("SearchAction");
  });
});

// ---------------------------------------------------------------------------
// articleJsonLd helper
// ---------------------------------------------------------------------------

describe("articleJsonLd", () => {
  it("test_article_jsonld_includes_required_fields", () => {
    const result = articleJsonLd(
      "Test Article",
      "Test description",
      "2026-02-20T10:00:00Z",
      "test-article",
    ) as Record<string, unknown>;
    expect(result).toMatchObject({
      "@context": "https://schema.org",
      "@type": "NewsArticle",
      headline: "Test Article",
      description: "Test description",
      datePublished: "2026-02-20T10:00:00Z",
    });
    expect(result.url).toContain("/newsletter/test-article");
  });

  it("test_article_jsonld_omits_date_when_null", () => {
    const result = articleJsonLd("No Date Article", "Description", null, "no-date") as Record<
      string,
      unknown
    >;
    expect(result.datePublished).toBeUndefined();
    expect(result.headline).toBe("No Date Article");
  });

  it("test_article_jsonld_includes_publisher", () => {
    const result = articleJsonLd("Title", "Desc", null, "slug") as Record<string, unknown>;
    const publisher = result.publisher as Record<string, unknown>;
    expect(publisher["@type"]).toBe("Organization");
    expect(publisher.name).toBe("Sinal");
  });
});

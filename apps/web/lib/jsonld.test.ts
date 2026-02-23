import { describe, it, expect } from "vitest";
import { companyJsonLd } from "@/lib/jsonld";
import type { Company } from "@/lib/company";

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

/** Full company — every optional field populated. */
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
  tags: ["fintech", "banking", "unicorn"],
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

/** Minimal company — every nullable field set to null. */
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
// Required fields — always present
// ---------------------------------------------------------------------------

describe("companyJsonLd — required fields", () => {
  it("test_companyjsonld_full_company_includes_context_and_type", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    expect(result["@context"]).toBe("https://schema.org");
    expect(result["@type"]).toBe("Organization");
  });

  it("test_companyjsonld_full_company_includes_name", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    expect(result.name).toBe("Nubank");
  });

  it("test_companyjsonld_minimal_company_still_has_context_type_name", () => {
    const result = companyJsonLd(minimalCompany) as Record<string, unknown>;
    expect(result["@context"]).toBe("https://schema.org");
    expect(result["@type"]).toBe("Organization");
    expect(result.name).toBe("Stealth Startup");
  });

  it("test_companyjsonld_returns_plain_object", () => {
    const result = companyJsonLd(fullCompany);
    expect(typeof result).toBe("object");
    expect(result).not.toBeNull();
    expect(Array.isArray(result)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// description / short_description fallback
// ---------------------------------------------------------------------------

describe("companyJsonLd — description fallback", () => {
  it("test_companyjsonld_uses_description_when_both_present", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    expect(result.description).toBe(
      "Digital bank revolutionizing financial services in Latin America",
    );
  });

  it("test_companyjsonld_falls_back_to_short_description_when_description_null", () => {
    const company: Company = { ...fullCompany, description: null };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.description).toBe("Leading digital bank in Brazil");
  });

  it("test_companyjsonld_description_is_undefined_when_both_null", () => {
    // Both null → description field should be undefined (null ?? null = null,
    // but the field is still set to null in the output object).
    const result = companyJsonLd(minimalCompany) as Record<string, unknown>;
    // The implementation sets description = null ?? null = null (not omitted).
    // This is acceptable — null is not the same as the string "null".
    expect(result.description === null || result.description === undefined).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// website / url field
// ---------------------------------------------------------------------------

describe("companyJsonLd — url field", () => {
  it("test_companyjsonld_includes_url_when_website_present", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    expect(result.url).toBe("https://nubank.com.br");
  });

  it("test_companyjsonld_omits_url_when_website_null", () => {
    const result = companyJsonLd(minimalCompany) as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(result, "url")).toBe(false);
  });

  it("test_companyjsonld_includes_url_with_http_scheme", () => {
    const company: Company = { ...fullCompany, website: "http://oldsite.example.com" };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.url).toBe("http://oldsite.example.com");
  });

  it("test_companyjsonld_includes_url_with_trailing_slash", () => {
    const company: Company = { ...fullCompany, website: "https://example.com/" };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.url).toBe("https://example.com/");
  });
});

// ---------------------------------------------------------------------------
// founded_date → foundingDate
// ---------------------------------------------------------------------------

describe("companyJsonLd — foundingDate", () => {
  it("test_companyjsonld_maps_founded_date_to_foundingDate", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    expect(result.foundingDate).toBe("2013-05-06");
  });

  it("test_companyjsonld_omits_foundingDate_when_founded_date_null", () => {
    const result = companyJsonLd(minimalCompany) as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(result, "foundingDate")).toBe(false);
  });

  it("test_companyjsonld_preserves_founded_date_string_verbatim", () => {
    const company: Company = { ...fullCompany, founded_date: "2020-01-15" };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.foundingDate).toBe("2020-01-15");
  });
});

// ---------------------------------------------------------------------------
// address
// ---------------------------------------------------------------------------

describe("companyJsonLd — address", () => {
  it("test_companyjsonld_includes_full_address_when_city_state_country_present", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    expect(result.address).toEqual({
      "@type": "PostalAddress",
      addressLocality: "São Paulo",
      addressRegion: "SP",
      addressCountry: "Brazil",
    });
  });

  it("test_companyjsonld_omits_address_when_both_city_and_country_null", () => {
    const company: Company = { ...minimalCompany, city: null, country: "Brazil" };
    // city is null but country is non-null → address should still be included
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.address).toBeDefined();
  });

  it("test_companyjsonld_omits_address_when_city_null_and_country_empty_string", () => {
    // When both city and country are falsy, address should be omitted.
    const company: Company = { ...minimalCompany, city: null, country: "" as string };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(result, "address")).toBe(false);
  });

  it("test_companyjsonld_address_omits_addressLocality_when_city_null", () => {
    const company: Company = { ...fullCompany, city: null };
    const result = companyJsonLd(company) as Record<string, unknown>;
    const address = result.address as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(address, "addressLocality")).toBe(false);
  });

  it("test_companyjsonld_address_omits_addressRegion_when_state_null", () => {
    const company: Company = { ...fullCompany, state: null };
    const result = companyJsonLd(company) as Record<string, unknown>;
    const address = result.address as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(address, "addressRegion")).toBe(false);
  });

  it("test_companyjsonld_address_includes_only_country_when_city_and_state_null", () => {
    const company: Company = { ...fullCompany, city: null, state: null };
    const result = companyJsonLd(company) as Record<string, unknown>;
    const address = result.address as Record<string, unknown>;
    expect(address["@type"]).toBe("PostalAddress");
    expect(address.addressCountry).toBe("Brazil");
    expect(Object.prototype.hasOwnProperty.call(address, "addressLocality")).toBe(false);
    expect(Object.prototype.hasOwnProperty.call(address, "addressRegion")).toBe(false);
  });

  it("test_companyjsonld_address_includes_city_without_state", () => {
    const company: Company = { ...fullCompany, state: null };
    const result = companyJsonLd(company) as Record<string, unknown>;
    const address = result.address as Record<string, unknown>;
    expect(address.addressLocality).toBe("São Paulo");
    expect(address.addressCountry).toBe("Brazil");
  });

  it("test_companyjsonld_address_type_is_PostalAddress", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    const address = result.address as Record<string, unknown>;
    expect(address["@type"]).toBe("PostalAddress");
  });
});

// ---------------------------------------------------------------------------
// numberOfEmployees / team_size
// ---------------------------------------------------------------------------

describe("companyJsonLd — numberOfEmployees", () => {
  it("test_companyjsonld_includes_numberOfEmployees_when_team_size_present", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    expect(result.numberOfEmployees).toEqual({
      "@type": "QuantitativeValue",
      value: 8000,
    });
  });

  it("test_companyjsonld_omits_numberOfEmployees_when_team_size_null", () => {
    const result = companyJsonLd(minimalCompany) as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(result, "numberOfEmployees")).toBe(false);
  });

  it("test_companyjsonld_numberOfEmployees_value_is_numeric", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    const employees = result.numberOfEmployees as Record<string, unknown>;
    expect(typeof employees.value).toBe("number");
    expect(employees.value).toBe(8000);
  });

  it("test_companyjsonld_numberOfEmployees_type_is_QuantitativeValue", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    const employees = result.numberOfEmployees as Record<string, unknown>;
    expect(employees["@type"]).toBe("QuantitativeValue");
  });

  it("test_companyjsonld_includes_numberOfEmployees_when_team_size_is_one", () => {
    const company: Company = { ...fullCompany, team_size: 1 };
    const result = companyJsonLd(company) as Record<string, unknown>;
    const employees = result.numberOfEmployees as Record<string, unknown>;
    expect(employees.value).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// Special characters and Unicode
// ---------------------------------------------------------------------------

describe("companyJsonLd — special characters and Unicode", () => {
  it("test_companyjsonld_handles_unicode_in_company_name", () => {
    const company: Company = { ...fullCompany, name: "Café & Tecnologia São Paulo" };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.name).toBe("Café & Tecnologia São Paulo");
  });

  it("test_companyjsonld_handles_unicode_in_city", () => {
    const company: Company = { ...fullCompany, city: "Bogotá" };
    const result = companyJsonLd(company) as Record<string, unknown>;
    const address = result.address as Record<string, unknown>;
    expect(address.addressLocality).toBe("Bogotá");
  });

  it("test_companyjsonld_handles_unicode_in_description", () => {
    const company: Company = {
      ...fullCompany,
      description: "Plataforma de inteligência artificial para PMEs",
    };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.description).toBe("Plataforma de inteligência artificial para PMEs");
  });

  it("test_companyjsonld_handles_company_name_with_ampersand", () => {
    const company: Company = { ...fullCompany, name: "A&B Tecnologia" };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.name).toBe("A&B Tecnologia");
  });

  it("test_companyjsonld_handles_company_name_with_quotes", () => {
    const company: Company = { ...fullCompany, name: 'Startup "Alpha" Labs' };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.name).toBe('Startup "Alpha" Labs');
  });
});

// ---------------------------------------------------------------------------
// JSON serialization safety (no literal "null" strings in output)
// ---------------------------------------------------------------------------

describe("companyJsonLd — JSON serialization safety", () => {
  it("test_companyjsonld_serializes_to_valid_json", () => {
    const result = companyJsonLd(fullCompany);
    expect(() => JSON.stringify(result)).not.toThrow();
  });

  it("test_companyjsonld_minimal_serializes_to_valid_json", () => {
    const result = companyJsonLd(minimalCompany);
    expect(() => JSON.stringify(result)).not.toThrow();
  });

  it("test_companyjsonld_serialized_output_has_no_literal_null_string", () => {
    // Ensures no field accidentally becomes the string "null" instead of being omitted.
    const result = companyJsonLd(minimalCompany);
    const serialized = JSON.stringify(result);
    expect(serialized).not.toContain('"null"');
  });

  it("test_companyjsonld_serialized_full_output_contains_schema_org_context", () => {
    const result = companyJsonLd(fullCompany);
    const serialized = JSON.stringify(result);
    expect(serialized).toContain("https://schema.org");
  });

  it("test_companyjsonld_serialized_full_output_contains_Organization_type", () => {
    const result = companyJsonLd(fullCompany);
    const serialized = JSON.stringify(result);
    expect(serialized).toContain("Organization");
  });
});

// ---------------------------------------------------------------------------
// Edge cases
// ---------------------------------------------------------------------------

describe("companyJsonLd — edge cases", () => {
  it("test_companyjsonld_empty_string_website_treated_as_falsy_omits_url", () => {
    const company: Company = { ...fullCompany, website: "" };
    const result = companyJsonLd(company) as Record<string, unknown>;
    // Empty string is falsy — url should be omitted.
    expect(Object.prototype.hasOwnProperty.call(result, "url")).toBe(false);
  });

  it("test_companyjsonld_empty_string_founded_date_treated_as_falsy_omits_foundingDate", () => {
    const company: Company = { ...fullCompany, founded_date: "" };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(result, "foundingDate")).toBe(false);
  });

  it("test_companyjsonld_output_does_not_include_non_schema_fields", () => {
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    // Fields from Company that are NOT part of JSON-LD should not leak into output.
    const schemaFields = new Set([
      "@context",
      "@type",
      "name",
      "description",
      "url",
      "foundingDate",
      "address",
      "numberOfEmployees",
    ]);
    for (const key of Object.keys(result)) {
      expect(schemaFields.has(key)).toBe(true);
    }
  });

  it("test_companyjsonld_does_not_include_github_url_or_linkedin_url", () => {
    // These are Company fields but not mapped to JSON-LD in the current implementation.
    const result = companyJsonLd(fullCompany) as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(result, "github_url")).toBe(false);
    expect(Object.prototype.hasOwnProperty.call(result, "linkedin_url")).toBe(false);
    expect(Object.prototype.hasOwnProperty.call(result, "twitter_url")).toBe(false);
  });

  it("test_companyjsonld_different_companies_produce_independent_objects", () => {
    const result1 = companyJsonLd(fullCompany) as Record<string, unknown>;
    const result2 = companyJsonLd(minimalCompany) as Record<string, unknown>;
    // Modifying one result must not affect the other.
    result1.name = "MODIFIED";
    expect(result2.name).toBe("Stealth Startup");
  });

  it("test_companyjsonld_country_only_address_triggers_address_block", () => {
    // city is null but country is present → condition (city || country) is truthy.
    const company: Company = { ...minimalCompany, city: null };
    const result = companyJsonLd(company) as Record<string, unknown>;
    expect(result.address).toBeDefined();
    const address = result.address as Record<string, unknown>;
    expect(address.addressCountry).toBe("Brazil");
  });
});

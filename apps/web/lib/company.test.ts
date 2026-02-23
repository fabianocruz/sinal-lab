import { describe, it, expect } from "vitest";
import { SECTOR_OPTIONS } from "@/lib/company";
import type { Company } from "@/lib/company";

// ---------------------------------------------------------------------------
// SECTOR_OPTIONS
// ---------------------------------------------------------------------------

describe("SECTOR_OPTIONS", () => {
  it("test_sectoroptions_is_a_non_empty_array", () => {
    expect(Array.isArray(SECTOR_OPTIONS)).toBe(true);
    expect(SECTOR_OPTIONS.length).toBeGreaterThan(0);
  });

  it("test_sectoroptions_has_ten_entries", () => {
    expect(SECTOR_OPTIONS).toHaveLength(10);
  });

  it("test_sectoroptions_all_entries_are_non_empty_strings", () => {
    for (const sector of SECTOR_OPTIONS) {
      expect(typeof sector, `entry "${sector}" should be a string`).toBe("string");
      expect(sector.trim().length, `entry "${sector}" should not be blank`).toBeGreaterThan(0);
    }
  });

  it("test_sectoroptions_values_are_unique", () => {
    const unique = new Set(SECTOR_OPTIONS);
    expect(unique.size).toBe(SECTOR_OPTIONS.length);
  });

  it("test_sectoroptions_contains_Fintech", () => {
    expect(SECTOR_OPTIONS).toContain("Fintech");
  });

  it("test_sectoroptions_contains_SaaS", () => {
    expect(SECTOR_OPTIONS).toContain("SaaS");
  });

  it("test_sectoroptions_contains_AI_ML", () => {
    expect(SECTOR_OPTIONS).toContain("AI/ML");
  });

  it("test_sectoroptions_contains_Healthtech", () => {
    expect(SECTOR_OPTIONS).toContain("Healthtech");
  });

  it("test_sectoroptions_contains_Edtech", () => {
    expect(SECTOR_OPTIONS).toContain("Edtech");
  });

  it("test_sectoroptions_contains_E_commerce", () => {
    expect(SECTOR_OPTIONS).toContain("E-commerce");
  });

  it("test_sectoroptions_contains_Logistics", () => {
    expect(SECTOR_OPTIONS).toContain("Logistics");
  });

  it("test_sectoroptions_contains_Agritech", () => {
    expect(SECTOR_OPTIONS).toContain("Agritech");
  });

  it("test_sectoroptions_contains_Proptech", () => {
    expect(SECTOR_OPTIONS).toContain("Proptech");
  });

  it("test_sectoroptions_contains_HR_Tech", () => {
    expect(SECTOR_OPTIONS).toContain("HR Tech");
  });

  it("test_sectoroptions_no_entry_has_leading_or_trailing_whitespace", () => {
    for (const sector of SECTOR_OPTIONS) {
      expect(sector, `"${sector}" has leading/trailing whitespace`).toBe(sector.trim());
    }
  });

  it("test_sectoroptions_no_entry_is_null_or_undefined", () => {
    for (const sector of SECTOR_OPTIONS) {
      expect(sector).not.toBeNull();
      expect(sector).not.toBeUndefined();
    }
  });
});

// ---------------------------------------------------------------------------
// Company interface — runtime shape verification
//
// TypeScript interfaces are erased at runtime, so we verify shape by
// constructing objects that satisfy the interface and asserting field presence.
// ---------------------------------------------------------------------------

describe("Company interface shape", () => {
  /** A fully-populated Company object used to verify required fields. */
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

  /** A minimal Company with all nullable fields set to null. */
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

  const requiredFields: (keyof Company)[] = [
    "id",
    "name",
    "slug",
    "description",
    "short_description",
    "sector",
    "sub_sector",
    "city",
    "state",
    "country",
    "tags",
    "tech_stack",
    "founded_date",
    "team_size",
    "business_model",
    "website",
    "github_url",
    "linkedin_url",
    "twitter_url",
    "source_count",
    "status",
    "created_at",
  ];

  it("test_company_full_object_has_all_22_fields", () => {
    expect(requiredFields).toHaveLength(22);
    for (const field of requiredFields) {
      expect(
        Object.prototype.hasOwnProperty.call(fullCompany, field),
        `field "${field}" missing on fullCompany`,
      ).toBe(true);
    }
  });

  it("test_company_minimal_object_has_all_22_fields", () => {
    for (const field of requiredFields) {
      expect(
        Object.prototype.hasOwnProperty.call(minimalCompany, field),
        `field "${field}" missing on minimalCompany`,
      ).toBe(true);
    }
  });

  it("test_company_id_is_a_string", () => {
    expect(typeof fullCompany.id).toBe("string");
  });

  it("test_company_name_is_a_non_empty_string", () => {
    expect(typeof fullCompany.name).toBe("string");
    expect(fullCompany.name.length).toBeGreaterThan(0);
  });

  it("test_company_slug_is_a_non_empty_string", () => {
    expect(typeof fullCompany.slug).toBe("string");
    expect(fullCompany.slug.length).toBeGreaterThan(0);
  });

  it("test_company_country_is_a_non_empty_string", () => {
    expect(typeof fullCompany.country).toBe("string");
    expect(fullCompany.country.length).toBeGreaterThan(0);
  });

  it("test_company_source_count_is_a_number", () => {
    expect(typeof fullCompany.source_count).toBe("number");
  });

  it("test_company_status_is_a_string", () => {
    expect(typeof fullCompany.status).toBe("string");
  });

  it("test_company_created_at_is_a_string", () => {
    expect(typeof fullCompany.created_at).toBe("string");
  });

  it("test_company_tags_is_array_or_null", () => {
    expect(Array.isArray(fullCompany.tags)).toBe(true);
    expect(minimalCompany.tags).toBeNull();
  });

  it("test_company_tech_stack_is_array_or_null", () => {
    expect(Array.isArray(fullCompany.tech_stack)).toBe(true);
    expect(minimalCompany.tech_stack).toBeNull();
  });

  it("test_company_team_size_is_number_or_null", () => {
    expect(typeof fullCompany.team_size).toBe("number");
    expect(minimalCompany.team_size).toBeNull();
  });

  it("test_company_nullable_string_fields_accept_null", () => {
    const nullableStringFields: (keyof Company)[] = [
      "description",
      "short_description",
      "sector",
      "sub_sector",
      "city",
      "state",
      "founded_date",
      "business_model",
      "website",
      "github_url",
      "linkedin_url",
      "twitter_url",
    ];
    for (const field of nullableStringFields) {
      expect(minimalCompany[field], `field "${field}" should be null on minimalCompany`).toBeNull();
    }
  });

  it("test_company_required_non_nullable_fields_are_always_strings", () => {
    // These fields are required and must never be null.
    expect(typeof fullCompany.id).toBe("string");
    expect(typeof fullCompany.name).toBe("string");
    expect(typeof fullCompany.slug).toBe("string");
    expect(typeof fullCompany.country).toBe("string");
    expect(typeof fullCompany.status).toBe("string");
    expect(typeof fullCompany.created_at).toBe("string");
  });

  it("test_company_source_count_is_non_negative", () => {
    expect(fullCompany.source_count).toBeGreaterThanOrEqual(0);
    expect(minimalCompany.source_count).toBeGreaterThanOrEqual(0);
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { FALLBACK_NEWSLETTERS } from "@/lib/newsletter";

// Mock the fetchCompanies API call used by sitemap
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchCompanies: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 }),
  };
});

// ---------------------------------------------------------------------------
// sitemap
// ---------------------------------------------------------------------------

describe("sitemap", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it("test_sitemap_returns_array", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    expect(Array.isArray(result)).toBe(true);
  });

  it("test_sitemap_contains_5_static_pages", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const staticUrls = result.filter(
      (entry) => !entry.url.includes("/newsletter/") && !entry.url.includes("/startup/"),
    );
    expect(staticUrls).toHaveLength(5);
  });

  it("test_sitemap_contains_all_newsletter_slugs", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const newsletterUrls = result.filter((entry) => entry.url.includes("/newsletter/"));
    expect(newsletterUrls).toHaveLength(FALLBACK_NEWSLETTERS.length);
  });

  it("test_sitemap_total_is_5_plus_newsletters", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    // 5 static pages + newsletter pages (no company pages since fetch is mocked empty)
    expect(result).toHaveLength(5 + FALLBACK_NEWSLETTERS.length);
  });

  it("test_sitemap_homepage_has_priority_1", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const homepage = result.find((entry) => entry.url === "https://sinal.ai");
    expect(homepage).toBeDefined();
    expect(homepage!.priority).toBe(1.0);
  });

  it("test_sitemap_homepage_has_weekly_frequency", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const homepage = result.find((entry) => entry.url === "https://sinal.ai");
    expect(homepage!.changeFrequency).toBe("weekly");
  });

  it("test_sitemap_includes_sobre_page", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const sobre = result.find((entry) => entry.url.endsWith("/sobre"));
    expect(sobre).toBeDefined();
    expect(sobre!.changeFrequency).toBe("monthly");
    expect(sobre!.priority).toBe(0.7);
  });

  it("test_sitemap_includes_metodologia_page", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const metodologia = result.find((entry) => entry.url.endsWith("/metodologia"));
    expect(metodologia).toBeDefined();
  });

  it("test_sitemap_includes_newsletter_archive", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const archive = result.find(
      (entry) => entry.url.endsWith("/newsletter") && !entry.url.includes("/newsletter/"),
    );
    expect(archive).toBeDefined();
    expect(archive!.priority).toBe(0.9);
  });

  it("test_sitemap_includes_startups_page", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const startups = result.find(
      (entry) => entry.url.endsWith("/startups") && !entry.url.includes("/startup/"),
    );
    expect(startups).toBeDefined();
    expect(startups!.priority).toBe(0.9);
  });

  it("test_sitemap_newsletter_pages_have_never_frequency", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const newsletterUrls = result.filter((entry) => entry.url.includes("/newsletter/"));
    newsletterUrls.forEach((entry) => {
      expect(entry.changeFrequency).toBe("never");
    });
  });

  it("test_sitemap_newsletter_pages_have_priority_08", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const newsletterUrls = result.filter((entry) => entry.url.includes("/newsletter/"));
    newsletterUrls.forEach((entry) => {
      expect(entry.priority).toBe(0.8);
    });
  });

  it("test_sitemap_newsletter_urls_contain_slugs", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    FALLBACK_NEWSLETTERS.forEach((newsletter) => {
      const match = result.find((entry) => entry.url.includes(newsletter.slug));
      expect(match).toBeDefined();
    });
  });

  it("test_sitemap_newsletter_pages_have_lastmodified_dates", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const newsletterUrls = result.filter((entry) => entry.url.includes("/newsletter/"));
    newsletterUrls.forEach((entry) => {
      expect(entry.lastModified).toBeInstanceOf(Date);
    });
  });

  it("test_sitemap_excludes_login_page", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const login = result.find((entry) => entry.url.includes("/login"));
    expect(login).toBeUndefined();
  });

  it("test_sitemap_excludes_cadastro_page", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    const cadastro = result.find((entry) => entry.url.includes("/cadastro"));
    expect(cadastro).toBeUndefined();
  });

  it("test_sitemap_all_urls_start_with_base_url", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    result.forEach((entry) => {
      expect(entry.url).toMatch(/^https:\/\/sinal\.ai/);
    });
  });

  it("test_sitemap_all_entries_have_lastmodified", async () => {
    const { default: sitemap } = await import("./sitemap");
    const result = await sitemap();
    result.forEach((entry) => {
      expect(entry.lastModified).toBeDefined();
    });
  });
});

// ---------------------------------------------------------------------------
// robots
// ---------------------------------------------------------------------------

describe("robots", () => {
  it("test_robots_returns_object_with_rules", async () => {
    const { default: robots } = await import("./robots");
    const result = robots();
    expect(result.rules).toBeDefined();
  });

  it("test_robots_has_wildcard_useragent", async () => {
    const { default: robots } = await import("./robots");
    const result = robots();
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    const wildcard = rules.find((r) => r.userAgent === "*");
    expect(wildcard).toBeDefined();
  });

  it("test_robots_allows_root", async () => {
    const { default: robots } = await import("./robots");
    const result = robots();
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    const wildcard = rules.find((r) => r.userAgent === "*");
    expect(wildcard!.allow).toBe("/");
  });

  it("test_robots_disallows_login", async () => {
    const { default: robots } = await import("./robots");
    const result = robots();
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    const wildcard = rules.find((r) => r.userAgent === "*");
    expect(wildcard!.disallow).toContain("/login");
  });

  it("test_robots_disallows_cadastro", async () => {
    const { default: robots } = await import("./robots");
    const result = robots();
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    const wildcard = rules.find((r) => r.userAgent === "*");
    expect(wildcard!.disallow).toContain("/cadastro");
  });

  it("test_robots_disallows_api", async () => {
    const { default: robots } = await import("./robots");
    const result = robots();
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    const wildcard = rules.find((r) => r.userAgent === "*");
    expect(wildcard!.disallow).toContain("/api/");
  });

  it("test_robots_has_sitemap_url", async () => {
    const { default: robots } = await import("./robots");
    const result = robots();
    expect(result.sitemap).toBe("https://sinal.ai/sitemap.xml");
  });

  it("test_robots_disallows_exactly_3_paths", async () => {
    const { default: robots } = await import("./robots");
    const result = robots();
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    const wildcard = rules.find((r) => r.userAgent === "*");
    expect(wildcard!.disallow).toHaveLength(3);
  });
});

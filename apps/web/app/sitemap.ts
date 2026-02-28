import type { MetadataRoute } from "next";
import { FALLBACK_NEWSLETTERS, type Newsletter } from "@/lib/newsletter";
import { fetchCompanies, fetchArticles } from "@/lib/api";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sinal.ai";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE_URL, lastModified: new Date(), changeFrequency: "weekly", priority: 1.0 },
    {
      url: `${BASE_URL}/sobre`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${BASE_URL}/metodologia`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${BASE_URL}/newsletter`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${BASE_URL}/startups`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${BASE_URL}/artigos`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${BASE_URL}/developers`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      url: `${BASE_URL}/termos`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${BASE_URL}/contato`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.4,
    },
    {
      url: `${BASE_URL}/privacidade`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];

  const newsletterPages: MetadataRoute.Sitemap = FALLBACK_NEWSLETTERS.map((n: Newsletter) => ({
    url: `${BASE_URL}/newsletter/${n.slug}`,
    lastModified: new Date(n.dateISO),
    changeFrequency: "never" as const,
    priority: 0.8,
  }));

  // Fetch company slugs for programmatic SEO pages
  let companyPages: MetadataRoute.Sitemap = [];
  try {
    const data = await fetchCompanies({ limit: 100 });
    companyPages = data.items.map((c) => ({
      url: `${BASE_URL}/startup/${c.slug}`,
      lastModified: new Date(c.created_at),
      changeFrequency: "weekly" as const,
      priority: 0.7,
    }));
  } catch {
    // Silently fail — sitemap still works with static + newsletter pages
  }

  // Fetch article slugs for programmatic SEO pages
  let articlePages: MetadataRoute.Sitemap = [];
  try {
    const data = await fetchArticles({ limit: 100 });
    articlePages = data.items.map((a) => ({
      url: `${BASE_URL}/artigos/${a.slug}`,
      lastModified: a.published_at ? new Date(a.published_at) : new Date(),
      changeFrequency: "never" as const,
      priority: 0.7,
    }));
  } catch {
    // Silently fail — same pattern as companies
  }

  return [...staticPages, ...newsletterPages, ...companyPages, ...articlePages];
}

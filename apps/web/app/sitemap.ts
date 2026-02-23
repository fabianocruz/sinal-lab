import type { MetadataRoute } from "next";
import { FALLBACK_NEWSLETTERS, type Newsletter } from "@/lib/newsletter";
import { fetchCompanies } from "@/lib/api";

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

  return [...staticPages, ...newsletterPages, ...companyPages];
}

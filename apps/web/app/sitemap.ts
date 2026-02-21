import type { MetadataRoute } from "next";
import { MOCK_NEWSLETTERS } from "@/lib/newsletter";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sinal.ai";

export default function sitemap(): MetadataRoute.Sitemap {
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
  ];

  const newsletterPages: MetadataRoute.Sitemap = MOCK_NEWSLETTERS.map((n) => ({
    url: `${BASE_URL}/newsletter/${n.slug}`,
    lastModified: new Date(n.dateISO),
    changeFrequency: "never" as const,
    priority: 0.8,
  }));

  return [...staticPages, ...newsletterPages];
}

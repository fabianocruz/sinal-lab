import type { MetadataRoute } from "next";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sinal.ai";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/login", "/cadastro", "/api/", "/admin/", "/conta"],
      },
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}

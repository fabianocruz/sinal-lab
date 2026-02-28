/** JSON-LD structured data helpers for SEO. */

import type { Company } from "@/lib/company";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sinal.ai";

/** Generate Organization JSON-LD for a company page. */
export function companyJsonLd(company: Company): object {
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: company.name,
    description: company.description ?? company.short_description,
  };

  if (company.website) jsonLd.url = company.website;
  if (company.founded_date) jsonLd.foundingDate = company.founded_date;

  if (company.city || company.country) {
    jsonLd.address = {
      "@type": "PostalAddress",
      ...(company.city && { addressLocality: company.city }),
      ...(company.state && { addressRegion: company.state }),
      ...(company.country && { addressCountry: company.country }),
    };
  }

  if (company.team_size) {
    jsonLd.numberOfEmployees = {
      "@type": "QuantitativeValue",
      value: company.team_size,
    };
  }

  return jsonLd;
}

/** Generate Organization + WebSite JSON-LD for the homepage. */
export function homepageJsonLd(): object[] {
  return [
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: "Sinal",
      url: SITE_URL,
      description:
        "Inteligência essencial sobre o ecossistema tech da América Latina — pesquisada por agentes de IA, revisada por humanos.",
    },
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: "Sinal",
      url: SITE_URL,
      potentialAction: {
        "@type": "SearchAction",
        target: {
          "@type": "EntryPoint",
          urlTemplate: `${SITE_URL}/startups?search={search_term_string}`,
        },
        "query-input": "required name=search_term_string",
      },
    },
  ];
}

/** Generate NewsArticle JSON-LD for newsletter/article detail pages. */
export function articleJsonLd(
  title: string,
  description: string,
  datePublished: string | null,
  slug: string,
): object {
  return {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: title,
    description,
    ...(datePublished && { datePublished }),
    url: `${SITE_URL}/newsletter/${slug}`,
    publisher: {
      "@type": "Organization",
      name: "Sinal",
      url: SITE_URL,
    },
    author: {
      "@type": "Organization",
      name: "Sinal",
    },
  };
}

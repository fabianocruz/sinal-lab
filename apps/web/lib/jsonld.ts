/** JSON-LD structured data helpers for SEO. */

import type { Company } from "@/lib/company";

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

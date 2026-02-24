/** Company types matching the expanded CompanyResponse from the API. */

export interface Company {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  short_description: string | null;
  sector: string | null;
  sub_sector: string | null;
  city: string | null;
  state: string | null;
  country: string;
  tags: string[] | null;
  tech_stack: string[] | null;
  founded_date: string | null;
  team_size: number | null;
  business_model: string | null;
  funding_stage: string | null;
  total_funding_usd: number | null;
  is_trending: boolean | null;
  website: string | null;
  github_url: string | null;
  linkedin_url: string | null;
  twitter_url: string | null;
  source_count: number;
  status: string;
  created_at: string;
}

/** Sector options for the filter component. */
export const SECTOR_OPTIONS = [
  "Fintech",
  "E-commerce",
  "SaaS",
  "Healthtech",
  "Edtech",
  "Logistics",
  "Agritech",
  "AI/ML",
  "Proptech",
  "HR Tech",
] as const;

/** Country → flag emoji mapping for LATAM. */
export const COUNTRY_FLAGS: Record<string, string> = {
  Brasil: "\u{1F1E7}\u{1F1F7}",
  Brazil: "\u{1F1E7}\u{1F1F7}",
  "M\u00e9xico": "\u{1F1F2}\u{1F1FD}",
  Mexico: "\u{1F1F2}\u{1F1FD}",
  "Col\u00f4mbia": "\u{1F1E8}\u{1F1F4}",
  Colombia: "\u{1F1E8}\u{1F1F4}",
  Argentina: "\u{1F1E6}\u{1F1F7}",
  Chile: "\u{1F1E8}\u{1F1F1}",
  Peru: "\u{1F1F5}\u{1F1EA}",
  "Per\u00fa": "\u{1F1F5}\u{1F1EA}",
  Uruguay: "\u{1F1FA}\u{1F1FE}",
  "Costa Rica": "\u{1F1E8}\u{1F1F7}",
  Ecuador: "\u{1F1EA}\u{1F1E8}",
  "Panam\u00e1": "\u{1F1F5}\u{1F1E6}",
};

/** Get flag emoji for a country string. Defaults to globe. */
export function getCountryFlag(country: string): string {
  return COUNTRY_FLAGS[country] ?? "\u{1F30E}";
}

/** Sector → accent color hex (reuses agent color palette). */
export const SECTOR_COLORS: Record<string, string> = {
  Fintech: "#FF8A59",
  "AI/ML": "#59B4FF",
  SaaS: "#C459FF",
  "E-commerce": "#59FFB4",
  Healthtech: "#59B4FF",
  Edtech: "#C459FF",
  Logistics: "#FF8A59",
  Agritech: "#59FFB4",
  Proptech: "#59B4FF",
  "HR Tech": "#C459FF",
};

/** Funding stage → accent color hex. */
export const STAGE_COLORS: Record<string, string> = {
  "Pre-Seed": "#8A8A96",
  Seed: "#59FFB4",
  "Series A": "#59B4FF",
  "Series B": "#FF8A59",
  "Series C+": "#C459FF",
  Bootstrapped: "#8A8A96",
};

/** Get accent color for a company based on stage (preferred) or sector (fallback). */
export function getAccentColor(fundingStage: string | null, sector: string | null): string {
  if (fundingStage && STAGE_COLORS[fundingStage]) {
    return STAGE_COLORS[fundingStage];
  }
  if (sector && SECTOR_COLORS[sector]) {
    return SECTOR_COLORS[sector];
  }
  return "#8A8A96"; // ash fallback
}

/** Format funding amount as compact string (e.g. "$1.5M", "$200K"). */
export function formatFunding(usd: number | null): string | null {
  if (usd == null) return null;
  if (usd >= 1_000_000_000) return `$${(usd / 1_000_000_000).toFixed(1)}B`;
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(1)}M`;
  if (usd >= 1_000) return `$${(usd / 1_000).toFixed(0)}K`;
  return `$${usd.toFixed(0)}`;
}

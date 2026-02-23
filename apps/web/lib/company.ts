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

/** Type derived from SECTOR_OPTIONS for type-safe sector field. */
export type Sector = (typeof SECTOR_OPTIONS)[number];

/** Company types matching the expanded CompanyResponse from the API. */

export interface Company {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  short_description: string | null;
  sector: Sector | string | null;
  sub_sector: string | null;
  city: string | null;
  state: string | null;
  country: string;
  tags: string[] | null;
  tech_stack: string[] | null;
  founded_date: string | null;
  team_size: number | null;
  business_model: string | null;
  website: string | null;
  github_url: string | null;
  linkedin_url: string | null;
  twitter_url: string | null;
  source_count: number;
  status: string;
  created_at: string;
}

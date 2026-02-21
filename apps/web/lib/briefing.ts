/**
 * TypeScript types for the BriefingData email payload.
 *
 * Mirrors the Python TypedDicts in apps/api/services/email.py.
 * Used by the briefing composer to build rich newsletter emails.
 */

// ---------------------------------------------------------------------------
// Section item types
// ---------------------------------------------------------------------------

export interface RadarTrend {
  arrow: string; // "↑" or "↓"
  arrow_color: string; // hex color like "#59FFB4"
  title: string;
  context: string;
  url?: string;
  source_name?: string;
  why_it_matters?: string;
  metrics?: Record<string, number>;
}

export interface FundingDeal {
  stage: string; // "Serie B", "Serie A", "Seed", etc.
  description: string; // "Clip (MEX) · $50M · SoftBank + Viking Global"
  source_url?: string;
  company_name?: string;
  company_url?: string;
  lead_investors?: string[];
  country?: string;
  why_it_matters?: string;
}

export interface MercadoMovement {
  type: string; // "Launch", "M&A", "Pivot", "Hire"
  description: string;
  source_url?: string;
  company_name?: string;
  company_url?: string;
  sector?: string;
  country?: string;
  why_it_matters?: string;
}

// ---------------------------------------------------------------------------
// Full briefing payload
// ---------------------------------------------------------------------------

export interface BriefingData {
  // Identity
  edition_number: number;
  week_number: number;
  date_range: string; // "3–10 Fev 2026"

  // Header
  preview_text: string;
  opening_headline: string;
  opening_body: string;

  // SINTESE section
  sintese_title: string;
  sintese_paragraphs: string[];
  sintese_dq: string;
  sintese_sources: number;
  sintese_image_url?: string;
  sintese_image_alt?: string;

  // RADAR section
  radar_title: string;
  radar_trends: RadarTrend[];
  radar_dq: string;
  radar_sources: number;
  radar_image_url?: string;
  radar_image_alt?: string;

  // CODIGO section
  codigo_title: string;
  codigo_body: string;
  codigo_url: string;

  // FUNDING section
  funding_count: number;
  funding_total: string;
  funding_score: string;
  funding_deals: FundingDeal[];
  funding_remaining: number;
  funding_url: string;

  // MERCADO section
  mercado_count: number;
  mercado_score: string;
  mercado_movements: MercadoMovement[];
  mercado_remaining: number;
  mercado_url: string;
}

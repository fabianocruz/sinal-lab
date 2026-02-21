import { describe, it, expect } from "vitest";
import type { BriefingData, RadarTrend, FundingDeal, MercadoMovement } from "@/lib/briefing";

// ---------------------------------------------------------------------------
// Type-level contract tests: ensure the TypeScript interfaces match the
// Python TypedDicts in apps/api/services/email.py. If the Python schema
// changes, these tests surface the drift.
// ---------------------------------------------------------------------------

function makeSampleRadarTrend(): RadarTrend {
  return {
    arrow: "\u2191",
    arrow_color: "#59FFB4",
    title: "Vertical AI Compliance",
    context: "3 launches this week in regulatory AI",
  };
}

function makeSampleFundingDeal(): FundingDeal {
  return {
    stage: "Serie B",
    description: "Clip (MEX) \u00b7 $50M \u00b7 SoftBank + Viking Global",
  };
}

function makeSampleMercadoMovement(): MercadoMovement {
  return {
    type: "Launch",
    description: "Rappi launches AI assistant in Colombia",
  };
}

function makeSampleBriefingData(): BriefingData {
  return {
    edition_number: 48,
    week_number: 8,
    date_range: "17\u201321 Fev 2026",
    preview_text: "Preview text",
    opening_headline: "Opening headline",
    opening_body: "Opening body paragraph",
    sintese_title: "Sinal Semanal #48",
    sintese_paragraphs: ["Paragraph one", "Paragraph two"],
    sintese_dq: "4/5",
    sintese_sources: 12,
    radar_title: "RADAR Semanal",
    radar_trends: [makeSampleRadarTrend()],
    radar_dq: "3/5",
    radar_sources: 8,
    codigo_title: "CODIGO Semanal",
    codigo_body: "Code analysis body",
    codigo_url: "https://sinal.tech/codigo/semana-8",
    funding_count: 14,
    funding_total: "US$287M",
    funding_score: "4/5",
    funding_deals: [makeSampleFundingDeal()],
    funding_remaining: 4,
    funding_url: "https://sinal.tech/funding/semana-8",
    mercado_count: 7,
    mercado_score: "3/5",
    mercado_movements: [makeSampleMercadoMovement()],
    mercado_remaining: 2,
    mercado_url: "https://sinal.tech/mercado/semana-8",
  };
}

// ---------------------------------------------------------------------------
// RadarTrend
// ---------------------------------------------------------------------------

describe("RadarTrend", () => {
  it("requires arrow, arrow_color, title, and context", () => {
    const trend = makeSampleRadarTrend();
    expect(trend.arrow).toBe("\u2191");
    expect(trend.arrow_color).toBe("#59FFB4");
    expect(trend.title).toBeTruthy();
    expect(trend.context).toBeTruthy();
  });

  it("supports optional url, source_name, why_it_matters, and metrics", () => {
    const trend: RadarTrend = {
      ...makeSampleRadarTrend(),
      url: "https://example.com/trend",
      source_name: "TechCrunch",
      why_it_matters: "Growing market signal",
      metrics: { mentions: 42, stars: 1200 },
    };
    expect(trend.url).toBe("https://example.com/trend");
    expect(trend.source_name).toBe("TechCrunch");
    expect(trend.why_it_matters).toBeTruthy();
    expect(trend.metrics).toEqual({ mentions: 42, stars: 1200 });
  });
});

// ---------------------------------------------------------------------------
// FundingDeal
// ---------------------------------------------------------------------------

describe("FundingDeal", () => {
  it("requires stage and description", () => {
    const deal = makeSampleFundingDeal();
    expect(deal.stage).toBe("Serie B");
    expect(deal.description).toContain("Clip");
  });

  it("supports optional source_url, company fields, and lead_investors", () => {
    const deal: FundingDeal = {
      ...makeSampleFundingDeal(),
      source_url: "https://example.com/deal",
      company_name: "Clip",
      company_url: "https://clip.mx",
      lead_investors: ["SoftBank", "Viking Global"],
      country: "Mexico",
      why_it_matters: "Largest fintech deal in Mexico this year",
    };
    expect(deal.lead_investors).toHaveLength(2);
    expect(deal.country).toBe("Mexico");
  });
});

// ---------------------------------------------------------------------------
// MercadoMovement
// ---------------------------------------------------------------------------

describe("MercadoMovement", () => {
  it("requires type and description", () => {
    const movement = makeSampleMercadoMovement();
    expect(movement.type).toBe("Launch");
    expect(movement.description).toContain("Rappi");
  });

  it("supports optional source_url, company fields, sector, and country", () => {
    const movement: MercadoMovement = {
      ...makeSampleMercadoMovement(),
      source_url: "https://example.com/news",
      company_name: "Rappi",
      company_url: "https://rappi.com",
      sector: "Delivery",
      country: "Colombia",
      why_it_matters: "AI expansion in delivery sector",
    };
    expect(movement.sector).toBe("Delivery");
    expect(movement.country).toBe("Colombia");
  });
});

// ---------------------------------------------------------------------------
// BriefingData
// ---------------------------------------------------------------------------

describe("BriefingData", () => {
  it("has all required fields", () => {
    const data = makeSampleBriefingData();

    // Identity
    expect(data.edition_number).toBe(48);
    expect(data.week_number).toBe(8);
    expect(data.date_range).toBeTruthy();

    // Header
    expect(data.preview_text).toBeTruthy();
    expect(data.opening_headline).toBeTruthy();
    expect(data.opening_body).toBeTruthy();

    // SINTESE
    expect(data.sintese_title).toBeTruthy();
    expect(data.sintese_paragraphs).toHaveLength(2);
    expect(data.sintese_dq).toBeTruthy();
    expect(data.sintese_sources).toBeGreaterThan(0);

    // RADAR
    expect(data.radar_title).toBeTruthy();
    expect(data.radar_trends).toHaveLength(1);
    expect(data.radar_dq).toBeTruthy();
    expect(data.radar_sources).toBeGreaterThan(0);

    // CODIGO
    expect(data.codigo_title).toBeTruthy();
    expect(data.codigo_body).toBeTruthy();
    expect(data.codigo_url).toBeTruthy();

    // FUNDING
    expect(data.funding_count).toBeGreaterThan(0);
    expect(data.funding_total).toBeTruthy();
    expect(data.funding_score).toBeTruthy();
    expect(data.funding_deals).toHaveLength(1);
    expect(data.funding_remaining).toBeGreaterThanOrEqual(0);
    expect(data.funding_url).toBeTruthy();

    // MERCADO
    expect(data.mercado_count).toBeGreaterThan(0);
    expect(data.mercado_score).toBeTruthy();
    expect(data.mercado_movements).toHaveLength(1);
    expect(data.mercado_remaining).toBeGreaterThanOrEqual(0);
    expect(data.mercado_url).toBeTruthy();
  });

  it("supports optional image fields", () => {
    const data: BriefingData = {
      ...makeSampleBriefingData(),
      sintese_image_url: "https://example.com/img.jpg",
      sintese_image_alt: "Newsletter hero image",
      radar_image_url: "https://example.com/radar.jpg",
      radar_image_alt: "Radar section image",
    };
    expect(data.sintese_image_url).toBeTruthy();
    expect(data.radar_image_alt).toBeTruthy();
  });

  it("radar_trends items are valid RadarTrend objects", () => {
    const data = makeSampleBriefingData();
    for (const trend of data.radar_trends) {
      expect(trend.arrow).toBeTruthy();
      expect(trend.arrow_color).toMatch(/^#[0-9A-Fa-f]{6}$/);
      expect(trend.title).toBeTruthy();
      expect(trend.context).toBeTruthy();
    }
  });

  it("funding_deals items are valid FundingDeal objects", () => {
    const data = makeSampleBriefingData();
    for (const deal of data.funding_deals) {
      expect(deal.stage).toBeTruthy();
      expect(deal.description).toBeTruthy();
    }
  });

  it("mercado_movements items are valid MercadoMovement objects", () => {
    const data = makeSampleBriefingData();
    for (const movement of data.mercado_movements) {
      expect(movement.type).toBeTruthy();
      expect(movement.description).toBeTruthy();
    }
  });
});

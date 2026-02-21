import { ImageResponse } from "next/og";
import { AGENT_HEX } from "@/lib/newsletter";
import { mapApiToNewsletter, FALLBACK_NEWSLETTERS } from "@/lib/newsletter";
import type { ContentApiItem } from "@/lib/newsletter";

export const runtime = "edge";
export const alt = "Sinal Newsletter";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// The five agent colors used in the bottom gradient bar, in fixed display order.
const GRADIENT_SEGMENTS: string[] = [
  "#E8FF59", // sintese
  "#59FFB4", // radar
  "#59B4FF", // codigo
  "#FF8A59", // funding
  "#C459FF", // mercado
];

// Palette constants — mirrors tailwind config values.
const COLOR = {
  black: "#0A0A0B",
  graphite: "#1A1A1F",
  ash: "#8A8A96",
  signal: "#E8FF59",
  white: "#FAFAF8",
} as const;

async function fetchApiItem(slug: string): Promise<ContentApiItem | null> {
  try {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(`${base}/api/content/${slug}`);
    if (!response.ok) return null;
    return response.json() as Promise<ContentApiItem>;
  } catch {
    return null;
  }
}

export default async function Image({ params }: { params: { slug: string } }) {
  // Try the live API first, then fall back to static fallback data.
  const apiItem = await fetchApiItem(params.slug);

  const newsletter = apiItem
    ? mapApiToNewsletter(apiItem, 0)
    : (FALLBACK_NEWSLETTERS.find((n) => n.slug === params.slug) ?? null);

  const agentColor = newsletter ? AGENT_HEX[newsletter.agent] : COLOR.signal;

  // --- Generic fallback when slug is not found anywhere ---
  if (!newsletter) {
    return new ImageResponse(
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          backgroundColor: COLOR.black,
          padding: "60px",
        }}
      >
        {/* Wordmark */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontFamily: "Georgia, serif",
              fontSize: "40px",
              color: COLOR.white,
              letterSpacing: "-0.5px",
            }}
          >
            Sinal
          </span>
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: COLOR.signal,
            }}
          />
        </div>

        {/* Tagline */}
        <div
          style={{
            display: "flex",
            marginTop: "auto",
            fontFamily: "Georgia, serif",
            fontSize: "28px",
            color: COLOR.ash,
          }}
        >
          Inteligência aberta para quem constrói.
        </div>

        {/* Bottom gradient bar */}
        <div
          style={{
            display: "flex",
            position: "absolute",
            bottom: "0",
            left: "0",
            width: "100%",
            height: "6px",
          }}
        >
          {GRADIENT_SEGMENTS.map((color, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                flex: 1,
                backgroundColor: color,
              }}
            />
          ))}
        </div>
      </div>,
      { ...size },
    );
  }

  // --- Newsletter-specific OG image ---
  const editionLine = `Edição #${newsletter.edition} · ${newsletter.date}`;

  return new ImageResponse(
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        backgroundColor: COLOR.black,
        padding: "60px",
        position: "relative",
      }}
    >
      {/* Top row: wordmark (left) + agent badge (right) */}
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
        }}
      >
        {/* Wordmark */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontFamily: "Georgia, serif",
              fontSize: "36px",
              color: COLOR.white,
              letterSpacing: "-0.5px",
            }}
          >
            Sinal
          </span>
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: COLOR.signal,
              marginTop: "2px",
            }}
          />
        </div>

        {/* Agent badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            paddingTop: "8px",
            paddingBottom: "8px",
            paddingLeft: "18px",
            paddingRight: "18px",
            borderRadius: "6px",
            backgroundColor: `${agentColor}22`,
            border: `1px solid ${agentColor}44`,
            fontFamily: "monospace",
            fontSize: "15px",
            fontWeight: 700,
            letterSpacing: "2px",
            color: agentColor,
          }}
        >
          {newsletter.agentLabel}
        </div>
      </div>

      {/* Center block: title + edition line */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          flex: 1,
          justifyContent: "center",
          paddingTop: "40px",
          paddingBottom: "40px",
        }}
      >
        {/* Title — max 3 lines */}
        <div
          style={{
            display: "flex",
            fontFamily: "Georgia, serif",
            fontSize: "40px",
            lineHeight: "1.25",
            color: COLOR.white,
            maxWidth: "900px",
            overflow: "hidden",
            // Satori supports webkit line clamp via display:-webkit-box
            // but the outer flex wrapper is required for it to engage.
          }}
        >
          <span
            style={{
              display: "-webkit-box",
              WebkitLineClamp: 3,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {newsletter.title}
          </span>
        </div>

        {/* Edition + date line */}
        <div
          style={{
            display: "flex",
            marginTop: "20px",
            fontFamily: "monospace",
            fontSize: "16px",
            color: COLOR.ash,
            letterSpacing: "0.5px",
          }}
        >
          {editionLine}
        </div>
      </div>

      {/* Bottom gradient bar — spans full width, ignores parent padding */}
      <div
        style={{
          display: "flex",
          position: "absolute",
          bottom: "0",
          left: "0",
          width: "1200px",
          height: "6px",
        }}
      >
        {GRADIENT_SEGMENTS.map((color, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              flex: 1,
              backgroundColor: color,
            }}
          />
        ))}
      </div>
    </div>,
    { ...size },
  );
}

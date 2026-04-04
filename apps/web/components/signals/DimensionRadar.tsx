"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

// Canonical labels in Portuguese for each dimension key
const DIMENSION_LABELS: Record<string, string> = {
  volume: "Volume",
  velocity: "Velocidade",
  authority: "Autoridade",
  cross_platform: "Cross-Platform",
  sentiment: "Sentimento",
  new_entrants: "Novos Entrantes",
  maturity: "Maturidade",
  commercial: "Comercial",
};

interface DimensionRadarProps {
  dimensions: Record<string, number>;
  accentColor?: string;
}

interface TooltipPayloadItem {
  name: string;
  value: number;
  payload: { dimension: string; value: number; label: string };
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="rounded-lg border border-[rgba(255,255,255,0.1)] bg-[#1A1A22] px-3 py-2 shadow-lg">
      <p className="font-mono text-[11px] text-ash">{item.payload.label}</p>
      <p className="font-mono text-[13px] text-sinal-white">{Math.round(item.value * 100)}</p>
    </div>
  );
}

export default function DimensionRadar({
  dimensions,
  accentColor = "#E8FF59",
}: DimensionRadarProps) {
  // Build data array: use known keys in a fixed order, fall back to raw key names
  const orderedKeys = [
    "volume",
    "velocity",
    "authority",
    "cross_platform",
    "sentiment",
    "new_entrants",
    "maturity",
    "commercial",
  ];

  // Include keys from the data that aren't in our ordered list
  const allKeys = [
    ...orderedKeys.filter((k) => k in dimensions),
    ...Object.keys(dimensions).filter((k) => !orderedKeys.includes(k)),
  ];

  const data = allKeys.map((key) => ({
    dimension: key,
    label: DIMENSION_LABELS[key] ?? key.replace(/_/g, " "),
    value: Math.min(Math.max(Number(dimensions[key]) || 0, 0), 1),
  }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="font-mono text-[12px] text-ash">Sem dados de dimensoes</p>
      </div>
    );
  }

  return (
    <div className="w-full min-w-[260px]">
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
          <PolarGrid stroke="rgba(255,255,255,0.08)" gridType="polygon" />
          <PolarAngleAxis
            dataKey="label"
            tick={{
              fill: "#8A8A96",
              fontSize: 10,
              fontFamily: "var(--font-mono, monospace)",
            }}
          />
          <Radar
            name="Score"
            dataKey="value"
            stroke={accentColor}
            fill={accentColor}
            fillOpacity={0.15}
            strokeWidth={1.5}
            dot={{ r: 3, fill: accentColor, strokeWidth: 0 }}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

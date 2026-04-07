"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { PLATFORM_COLORS, PLATFORM_LABELS } from "@/lib/signal";

export interface PlatformHeatmapRow {
  theme: string;
  twitter: number;
  reddit: number;
  bluesky: number;
  rss: number;
  [key: string]: string | number;
}

interface PlatformHeatmapProps {
  data: PlatformHeatmapRow[];
}

const PLATFORMS = ["twitter", "reddit", "bluesky", "rss", "web", "youtube"] as const;

interface TooltipPayloadItem {
  name: string;
  value: number;
  fill: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-[rgba(255,255,255,0.1)] bg-[#1A1A22] px-3 py-2 shadow-lg">
      <p className="mb-1.5 font-mono text-[11px] text-sinal-white">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.fill }}
          />
          <span className="font-mono text-[11px] text-ash">
            {PLATFORM_LABELS[entry.name] ?? entry.name}
          </span>
          <span className="font-mono text-[11px] text-sinal-white">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function PlatformHeatmap({ data }: PlatformHeatmapProps) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="font-mono text-[12px] text-ash">Sem dados de plataforma</p>
      </div>
    );
  }

  // Truncate long theme names for the axis
  const chartData = data.map((row) => ({
    ...row,
    themeShort: row.theme.length > 20 ? row.theme.slice(0, 18) + "…" : row.theme,
  }));

  return (
    <div className="w-full min-w-[300px]">
      <ResponsiveContainer width="100%" height={Math.max(180, data.length * 44)}>
        <BarChart
          layout="vertical"
          data={chartData}
          margin={{ top: 0, right: 16, bottom: 0, left: 8 }}
          barCategoryGap="30%"
          barGap={2}
        >
          <XAxis
            type="number"
            tick={{ fill: "#4A4A56", fontSize: 9, fontFamily: "var(--font-mono, monospace)" }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="themeShort"
            width={110}
            tick={{ fill: "#8A8A96", fontSize: 10, fontFamily: "var(--font-mono, monospace)" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          {PLATFORMS.map((platform) => (
            <Bar
              key={platform}
              dataKey={platform}
              name={platform}
              stackId="a"
              radius={[0, 0, 0, 0]}
            >
              {chartData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={PLATFORM_COLORS[platform] ?? "#4A4A56"}
                  fillOpacity={0.75}
                />
              ))}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Platform legend */}
      <div className="mt-3 flex flex-wrap gap-3">
        {PLATFORMS.map((p) => (
          <div key={p} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: PLATFORM_COLORS[p] }}
            />
            <span className="font-mono text-[10px] text-ash">{PLATFORM_LABELS[p] ?? p}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

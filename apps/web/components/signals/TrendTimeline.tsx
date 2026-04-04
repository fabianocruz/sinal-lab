"use client";

import { Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, ComposedChart } from "recharts";

export interface TrendTimelinePoint {
  week: string;
  score: number;
}

interface TrendTimelineProps {
  data: TrendTimelinePoint[];
  accentColor?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const value = payload[0]?.value ?? 0;
  return (
    <div className="rounded-lg border border-[rgba(255,255,255,0.1)] bg-[#1A1A22] px-3 py-2 shadow-lg">
      <p className="font-mono text-[10px] text-ash">{label}</p>
      <p className="font-mono text-[14px] text-sinal-white">{Math.round(value * 100)}</p>
    </div>
  );
}

export default function TrendTimeline({ data, accentColor = "#E8FF59" }: TrendTimelineProps) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="font-mono text-[12px] text-ash">Sem dados historicos</p>
      </div>
    );
  }

  // Gradient ID — needs to be unique enough not to collide across multiple charts on the page
  const gradientId = `trend-gradient-${accentColor.replace("#", "")}`;

  return (
    <div className="w-full min-w-[260px]">
      <ResponsiveContainer width="100%" height={140}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={accentColor} stopOpacity={0.25} />
              <stop offset="95%" stopColor={accentColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="week"
            tick={{ fill: "#4A4A56", fontSize: 9, fontFamily: "var(--font-mono, monospace)" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: "#4A4A56", fontSize: 9, fontFamily: "var(--font-mono, monospace)" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => String(Math.round(v * 100))}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ stroke: "rgba(255,255,255,0.1)", strokeWidth: 1 }}
          />
          <Area
            type="monotone"
            dataKey="score"
            stroke="none"
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke={accentColor}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 4, fill: accentColor, strokeWidth: 0 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

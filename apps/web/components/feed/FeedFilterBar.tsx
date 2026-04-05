"use client";

import React, { useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";

// ---------------------------------------------------------------------------
// Theme options — platform filter removed (curator already filtered by source)
// ---------------------------------------------------------------------------

const THEME_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "AI", label: "AI" },
  { value: "Fintech", label: "Fintech" },
  { value: "Banking", label: "Banking" },
];

// Category accent colors aligned with FeedItem
const THEME_COLORS: Record<string, string> = {
  AI: "#59FFB4",
  Fintech: "#E8FF59",
  Banking: "#59B4FF",
};

// ---------------------------------------------------------------------------
// Pill sub-component
// ---------------------------------------------------------------------------

interface PillProps {
  active: boolean;
  onClick: () => void;
  accentColor?: string;
  children: React.ReactNode;
}

function Pill({ active, onClick, accentColor, children }: PillProps) {
  const activeStyle = accentColor
    ? { backgroundColor: `${accentColor}18`, color: accentColor, borderColor: `${accentColor}40` }
    : undefined;

  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "shrink-0 rounded-lg border px-3 py-1.5 font-mono text-[12px] transition-all",
        active
          ? accentColor
            ? "font-semibold"
            : "border-signal bg-signal font-semibold text-sinal-black"
          : "border-[rgba(255,255,255,0.06)] bg-sinal-graphite text-ash hover:border-[rgba(255,255,255,0.12)] hover:bg-sinal-slate hover:text-sinal-white",
      ].join(" ")}
      style={active ? activeStyle : undefined}
      aria-pressed={active}
    >
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FeedFilterBar() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const activeTheme = searchParams.get("theme") ?? "";

  const applyTheme = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set("theme", value);
      } else {
        params.delete("theme");
      }
      // Reset to page 1 whenever filter changes
      params.delete("page");
      router.push(`/feed?${params.toString()}`);
    },
    [router, searchParams],
  );

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tema">
      {THEME_OPTIONS.map((opt) => (
        <Pill
          key={opt.value}
          active={activeTheme === opt.value}
          onClick={() => applyTheme(opt.value)}
          accentColor={opt.value ? THEME_COLORS[opt.value] : undefined}
        >
          {opt.label}
        </Pill>
      ))}
    </div>
  );
}

"use client";

import React, { useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SIGNAL_THEMES, THEME_COLORS } from "@/lib/signal";

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
      <Pill key="" active={activeTheme === ""} onClick={() => applyTheme("")}>
        Todos
      </Pill>
      {SIGNAL_THEMES.map((theme) => (
        <Pill
          key={theme.key}
          active={activeTheme === theme.key}
          onClick={() => applyTheme(theme.key)}
          accentColor={theme.color}
        >
          {theme.label}
        </Pill>
      ))}
    </div>
  );
}

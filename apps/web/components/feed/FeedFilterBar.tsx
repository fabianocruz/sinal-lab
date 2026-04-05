"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

// ---------------------------------------------------------------------------
// Filter options
// ---------------------------------------------------------------------------

const PLATFORM_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "twitter", label: "Twitter/X" },
  { value: "reddit", label: "Reddit" },
  { value: "bluesky", label: "Bluesky" },
  { value: "youtube", label: "YouTube" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "rss", label: "Newsletter" },
  { value: "polymarket", label: "Polymarket" },
];

const THEME_OPTIONS = [
  { value: "", label: "Todos os temas" },
  { value: "AI", label: "AI" },
  { value: "Fintech", label: "Fintech" },
  { value: "Banking", label: "Banking" },
];

// ---------------------------------------------------------------------------
// Pill sub-component
// ---------------------------------------------------------------------------

interface PillProps {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

function Pill({ active, onClick, children }: PillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "shrink-0 rounded-lg px-3 py-1.5 font-mono text-[12px] transition-all",
        active
          ? "bg-signal text-sinal-black font-semibold"
          : "bg-sinal-graphite text-ash hover:bg-sinal-slate hover:text-sinal-white border border-[rgba(255,255,255,0.06)]",
      ].join(" ")}
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

  const activePlatform = searchParams.get("platform") ?? "";
  const activeTheme = searchParams.get("theme") ?? "";

  const applyFilter = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      // Reset to page 1 whenever a filter changes
      params.delete("page");
      router.push(`/feed?${params.toString()}`);
    },
    [router, searchParams],
  );

  return (
    <div className="space-y-3" aria-label="Filtros do feed">
      {/* Platform pills */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por plataforma">
        {PLATFORM_OPTIONS.map((opt) => (
          <Pill
            key={opt.value}
            active={activePlatform === opt.value}
            onClick={() => applyFilter("platform", opt.value)}
          >
            {opt.label}
          </Pill>
        ))}
      </div>

      {/* Theme pills */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tema">
        {THEME_OPTIONS.map((opt) => (
          <Pill
            key={opt.value}
            active={activeTheme === opt.value}
            onClick={() => applyFilter("theme", opt.value)}
          >
            {opt.label}
          </Pill>
        ))}
      </div>
    </div>
  );
}

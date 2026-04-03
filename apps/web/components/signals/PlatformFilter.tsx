"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { PLATFORM_COLORS, PLATFORM_LABELS } from "@/lib/signal";

interface PlatformOption {
  key: string;
  label: string;
  color?: string;
}

const PLATFORM_OPTIONS: PlatformOption[] = [
  { key: "all", label: "Todos" },
  { key: "twitter", label: PLATFORM_LABELS.twitter, color: PLATFORM_COLORS.twitter },
  { key: "reddit", label: PLATFORM_LABELS.reddit, color: PLATFORM_COLORS.reddit },
  { key: "bluesky", label: PLATFORM_LABELS.bluesky, color: PLATFORM_COLORS.bluesky },
  { key: "linkedin", label: PLATFORM_LABELS.linkedin, color: PLATFORM_COLORS.linkedin },
];

export default function PlatformFilter() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const active = searchParams.get("platform") ?? "all";

  function handleSelect(key: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (key === "all") {
      params.delete("platform");
    } else {
      params.set("platform", key);
    }
    // Reset to page 1 whenever filter changes
    params.delete("page");
    router.push(`/signals?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por plataforma">
      {PLATFORM_OPTIONS.map((option) => {
        const isActive = active === option.key;
        const activeColor = option.color ?? "#FFFFFF";
        return (
          <button
            key={option.key}
            onClick={() => handleSelect(option.key)}
            aria-pressed={isActive}
            className="flex items-center gap-[6px] rounded-lg border px-[14px] py-[9px] font-mono text-[12px] uppercase tracking-[1px] transition-all duration-200 hover:text-sinal-white"
            style={
              isActive
                ? {
                    borderColor: activeColor,
                    backgroundColor: `${activeColor}14`,
                    color: activeColor,
                  }
                : {
                    borderColor: "rgba(255,255,255,0.06)",
                    color: "#7A7A8A",
                  }
            }
          >
            {option.color && (
              <span
                className="inline-block h-[6px] w-[6px] shrink-0 rounded-full"
                style={{ backgroundColor: option.color }}
                aria-hidden="true"
              />
            )}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

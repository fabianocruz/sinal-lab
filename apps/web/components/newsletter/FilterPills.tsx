"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { AGENT_HEX } from "@/lib/newsletter";

interface FilterOption {
  key: string;
  label: string;
  color?: string;
}

const FILTER_OPTIONS: FilterOption[] = [
  { key: "todos", label: "Todos" },
  { key: "sintese", label: "Síntese", color: AGENT_HEX.sintese },
  { key: "radar", label: "Radar", color: AGENT_HEX.radar },
  { key: "codigo", label: "Código", color: AGENT_HEX.codigo },
  { key: "funding", label: "Funding", color: AGENT_HEX.funding },
  { key: "mercado", label: "Mercado", color: AGENT_HEX.mercado },
];

export default function FilterPills() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const active = searchParams.get("agent") ?? "todos";

  function handleSelect(key: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (key === "todos") {
      params.delete("agent");
    } else {
      params.set("agent", key);
    }
    // Reset to page 1 whenever the filter changes.
    params.delete("page");
    router.push(`/newsletter?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por agente">
      {FILTER_OPTIONS.map((option) => {
        const isActive = active === option.key;
        // For "todos" pill when active, fall back to white
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

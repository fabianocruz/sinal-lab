"use client";

import { useRouter, useSearchParams } from "next/navigation";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Persona = "all" | "cto" | "vc" | "founder";

export interface PersonaOption {
  key: Persona;
  label: string;
  icon: string;
  description: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const PERSONA_OPTIONS: PersonaOption[] = [
  {
    key: "all",
    label: "Todos",
    icon: "◎",
    description: "Todos os sinais",
  },
  {
    key: "cto",
    label: "CTO / Tech Lead",
    icon: ">_",
    description: "Tecnologia e infraestrutura",
  },
  {
    key: "vc",
    label: "Investidor / VC",
    icon: "↗",
    description: "Oportunidades e mercado",
  },
  {
    key: "founder",
    label: "Fundador / CEO",
    icon: "◈",
    description: "Estrategia e produto",
  },
];

export const PERSONA_LABELS: Record<Persona, string> = {
  all: "Todos",
  cto: "CTO / Tech Lead",
  vc: "Investidor / VC",
  founder: "Fundador / CEO",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function resolvePersona(value: string | undefined): Persona {
  if (!value) return "all";
  if (value === "cto" || value === "vc" || value === "founder") return value;
  return "all";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface PersonaSelectorProps {
  activePersona: Persona;
}

export default function PersonaSelector({ activePersona }: PersonaSelectorProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function handleSelect(persona: Persona) {
    const params = new URLSearchParams(searchParams.toString());
    if (persona === "all") {
      params.delete("persona");
    } else {
      params.set("persona", persona);
    }
    router.push(`/signals?${params.toString()}`);
  }

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      role="group"
      aria-label="Filtrar por perfil de usuario"
    >
      <span className="mr-1 font-mono text-[10px] uppercase tracking-[1.5px] text-[#4A4A56]">
        Perfil
      </span>
      {PERSONA_OPTIONS.map((opt) => {
        const isActive = activePersona === opt.key;
        return (
          <button
            key={opt.key}
            onClick={() => handleSelect(opt.key)}
            aria-pressed={isActive}
            title={opt.description}
            className={[
              "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 font-mono text-[11px] transition-all duration-200",
              isActive
                ? "border-signal bg-[rgba(232,255,89,0.08)] text-signal"
                : "border-[rgba(255,255,255,0.06)] text-ash hover:border-[rgba(255,255,255,0.12)] hover:text-silver",
            ].join(" ")}
          >
            <span aria-hidden="true" className="text-[10px]">
              {opt.icon}
            </span>
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

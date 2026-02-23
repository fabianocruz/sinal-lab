"use client";

import GenericFilterPills from "@/components/ui/FilterPills";
import { AGENT_HEX } from "@/lib/newsletter";

const AGENT_OPTIONS = [
  { value: "sintese", label: "Síntese", color: AGENT_HEX.sintese },
  { value: "radar", label: "Radar", color: AGENT_HEX.radar },
  { value: "codigo", label: "Código", color: AGENT_HEX.codigo },
  { value: "funding", label: "Funding", color: AGENT_HEX.funding },
  { value: "mercado", label: "Mercado", color: AGENT_HEX.mercado },
];

export default function FilterPills() {
  return (
    <GenericFilterPills
      paramKey="agent"
      options={AGENT_OPTIONS}
      allLabel="Todos"
      basePath="/newsletter"
      aria-label="Filtrar por agente"
    />
  );
}

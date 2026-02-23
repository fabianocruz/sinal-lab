"use client";

import GenericFilterPills from "@/components/ui/FilterPills";
import { SECTOR_OPTIONS } from "@/lib/company";

const SECTOR_FILTER_OPTIONS = SECTOR_OPTIONS.map((sector) => ({
  value: sector,
  label: sector,
}));

export default function SectorFilter() {
  return (
    <GenericFilterPills
      paramKey="sector"
      options={SECTOR_FILTER_OPTIONS}
      allLabel="Todos"
      basePath="/startups"
      aria-label="Filtrar por setor"
    />
  );
}

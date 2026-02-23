"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { SECTOR_OPTIONS } from "@/lib/company";

export default function SectorFilter() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const active = searchParams.get("sector") ?? "todos";

  function handleSelect(key: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (key === "todos") {
      params.delete("sector");
    } else {
      params.set("sector", key);
    }
    params.delete("page");
    router.push(`/startups?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por setor">
      <button
        onClick={() => handleSelect("todos")}
        aria-pressed={active === "todos"}
        className={`rounded-lg border px-4 py-2 font-mono text-[11px] uppercase tracking-[1px] transition-all duration-200 ${
          active === "todos"
            ? "border-signal bg-[rgba(232,255,89,0.06)] text-signal"
            : "border-[rgba(255,255,255,0.06)] text-ash hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white"
        }`}
      >
        Todos
      </button>
      {SECTOR_OPTIONS.map((sector) => {
        const isActive = active === sector;
        return (
          <button
            key={sector}
            onClick={() => handleSelect(sector)}
            aria-pressed={isActive}
            className={`rounded-lg border px-4 py-2 font-mono text-[11px] uppercase tracking-[1px] transition-all duration-200 ${
              isActive
                ? "border-signal bg-[rgba(232,255,89,0.06)] text-signal"
                : "border-[rgba(255,255,255,0.06)] text-ash hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white"
            }`}
          >
            {sector}
          </button>
        );
      })}
    </div>
  );
}

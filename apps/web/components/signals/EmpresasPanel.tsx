"use client";

import { useState } from "react";
import Link from "next/link";
import type { Company } from "@/lib/company";
import { SECTOR_COLORS } from "@/lib/company";
import type { Signal } from "@/lib/signal";

// Sector filter pills shown at the top of the panel
const SECTOR_FILTERS = ["Fintech", "AI/ML", "SaaS", "Healthtech", "E-commerce"] as const;
type SectorFilter = (typeof SECTOR_FILTERS)[number] | "Todos";

interface MatchedCompany {
  company: Company;
  mentionCount: number;
  latestSnippet: string;
}

/**
 * Match known companies from the DB against signal texts.
 * Returns companies sorted by mention count descending.
 * Skips names with 3 chars or fewer to avoid false positives.
 */
function matchCompaniesAgainstSignals(companies: Company[], signals: Signal[]): MatchedCompany[] {
  if (companies.length === 0 || signals.length === 0) return [];

  const results: MatchedCompany[] = [];

  for (const company of companies) {
    const nameLower = company.name.toLowerCase();
    if (nameLower.length <= 3) continue;

    let count = 0;
    let latestSnippet = "";

    for (const signal of signals) {
      const textLower = signal.text.toLowerCase();
      if (textLower.includes(nameLower)) {
        count++;
        // Keep the snippet from the most recent signal that mentions the company
        if (!latestSnippet) {
          latestSnippet = signal.text.slice(0, 120).trimEnd();
          if (signal.text.length > 120) latestSnippet += "...";
        }
      }
    }

    if (count > 0) {
      results.push({ company, mentionCount: count, latestSnippet });
    }
  }

  return results.sort((a, b) => b.mentionCount - a.mentionCount);
}

interface EmpresaRowProps {
  matched: MatchedCompany;
  rank: number;
}

function EmpresaRow({ matched, rank }: EmpresaRowProps) {
  const { company, mentionCount, latestSnippet } = matched;
  const sectorColor = (company.sector && SECTOR_COLORS[company.sector]) || "#8A8A96";

  return (
    <div className="rounded-xl border border-sinal-slate bg-sinal-graphite px-5 py-4 transition-all duration-200 hover:border-[rgba(255,255,255,0.10)]">
      <div className="flex items-start gap-4">
        {/* Rank */}
        <span className="mt-[3px] w-5 shrink-0 text-right font-mono text-[12px] text-[#4A4A56]">
          {rank}
        </span>

        {/* Main content */}
        <div className="min-w-0 flex-1">
          {/* Top row: name + sector + city + mention count */}
          <div className="mb-1.5 flex flex-wrap items-center gap-2">
            <Link
              href={`/startup/${company.slug}`}
              className="font-mono text-[14px] font-semibold text-sinal-white transition-colors hover:text-signal"
            >
              {company.name}
            </Link>

            {/* "No nosso mapa" badge */}
            <Link
              href={`/startup/${company.slug}`}
              className="rounded border border-[rgba(89,255,180,0.2)] px-1.5 py-[2px] font-mono text-[9px] uppercase tracking-[0.8px] text-signal transition-colors hover:border-signal"
              aria-label={`${company.name} esta no nosso mapa de startups`}
            >
              No nosso mapa
            </Link>

            {company.sector && (
              <span
                className="rounded px-2 py-[2px] font-mono text-[10px]"
                style={{ color: sectorColor, backgroundColor: `${sectorColor}14` }}
              >
                {company.sector}
              </span>
            )}

            {company.city && <span className="font-mono text-[11px] text-ash">{company.city}</span>}
          </div>

          {/* Signal snippet */}
          {latestSnippet && (
            <p className="text-[12px] leading-[1.5] text-[#4A4A56]">{latestSnippet}</p>
          )}
        </div>

        {/* Mention count */}
        <div className="shrink-0 text-right">
          <span className="font-mono text-[16px] font-semibold text-sinal-white">
            {mentionCount}
          </span>
          <p className="font-mono text-[10px] uppercase tracking-[0.5px] text-[#4A4A56]">mencoes</p>
        </div>
      </div>
    </div>
  );
}

interface EmpresasPanelProps {
  companies: Company[];
  signals: Signal[];
}

export default function EmpresasPanel({ companies, signals }: EmpresasPanelProps) {
  const [activeSector, setActiveSector] = useState<SectorFilter>("Todos");

  const allMatches = matchCompaniesAgainstSignals(companies, signals);

  const filtered =
    activeSector === "Todos"
      ? allMatches
      : allMatches.filter((m) => m.company.sector === activeSector);

  return (
    <div id="panel-empresas" role="tabpanel" aria-label="Empresas no Sinal" className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="mb-1 font-display text-[22px] text-sinal-white">Empresas nos Sinais</h2>
          <p className="text-[13px] text-ash">
            Empresas do nosso mapa mencionadas em sinais coletados esta semana.
          </p>
        </div>
        {allMatches.length > 0 && (
          <span className="font-mono text-[12px] text-[#4A4A56]">
            {allMatches.length} empresa{allMatches.length !== 1 ? "s" : ""} detectada
            {allMatches.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Sector filter pills */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por setor">
        <button
          onClick={() => setActiveSector("Todos")}
          className={[
            "rounded-lg border px-3 py-1.5 font-mono text-[11px] transition-all",
            activeSector === "Todos"
              ? "border-sinal-slate bg-sinal-graphite text-sinal-white"
              : "border-[rgba(255,255,255,0.06)] text-ash hover:border-sinal-slate hover:text-silver",
          ].join(" ")}
        >
          Todos
        </button>
        {SECTOR_FILTERS.map((sector) => {
          const color = SECTOR_COLORS[sector] ?? "#8A8A96";
          const isActive = activeSector === sector;
          return (
            <button
              key={sector}
              onClick={() => setActiveSector(sector)}
              className={[
                "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 font-mono text-[11px] transition-all",
                isActive
                  ? "border-sinal-slate bg-sinal-graphite text-sinal-white"
                  : "border-[rgba(255,255,255,0.06)] text-ash hover:border-sinal-slate hover:text-silver",
              ].join(" ")}
            >
              <span
                className="inline-block h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: color }}
                aria-hidden="true"
              />
              {sector}
            </button>
          );
        })}
      </div>

      {/* Company list */}
      {filtered.length > 0 ? (
        <div className="space-y-2">
          {filtered.map((matched, i) => (
            <EmpresaRow key={matched.company.id} matched={matched} rank={i + 1} />
          ))}
        </div>
      ) : (
        <div className="py-16 text-center">
          <p className="mb-1 text-[15px] text-ash">
            Nenhuma empresa detectada nos sinais desta semana
          </p>
          <p className="text-[13px] text-[#4A4A56]">
            {activeSector !== "Todos"
              ? `Nenhuma empresa do setor ${activeSector} foi mencionada nos sinais coletados.`
              : "As empresas do nosso mapa serao cruzadas com os sinais apos a proxima coleta do agente RADAR."}
          </p>
        </div>
      )}
    </div>
  );
}

"use client";

import { useState, useMemo } from "react";
import ClusterCard from "@/components/signals/ClusterCard";
import SignalCard from "@/components/signals/SignalCard";
import DimensionRadar from "@/components/signals/DimensionRadar";
import type { Signal, SignalCluster } from "@/lib/signal";

// Theme definitions with accent colors
const TEMAS = [
  { key: "Todos", label: "Todos", color: "#8A8A96" },
  { key: "AI", label: "AI", color: "#59FFB4" },
  { key: "Fintech", label: "Fintech", color: "#E8FF59" },
  { key: "AI in Banking", label: "AI in Banking", color: "#59B4FF" },
] as const;

type TemaKey = (typeof TEMAS)[number]["key"];

/**
 * Aggregate dimension scores across a set of clusters by averaging.
 * Returns an empty object when no clusters are provided.
 */
function aggregateDimensions(clusters: SignalCluster[]): Record<string, number> {
  if (clusters.length === 0) return {};

  const sums: Record<string, number> = {};
  const counts: Record<string, number> = {};

  for (const cluster of clusters) {
    for (const [key, value] of Object.entries(cluster.dimensions)) {
      sums[key] = (sums[key] ?? 0) + value;
      counts[key] = (counts[key] ?? 0) + 1;
    }
  }

  const result: Record<string, number> = {};
  for (const key of Object.keys(sums)) {
    result[key] = sums[key] / counts[key];
  }
  return result;
}

interface TemasPanelProps {
  clusters: SignalCluster[];
  signals: Signal[];
}

export default function TemasPanel({ clusters, signals }: TemasPanelProps) {
  const [activeTema, setActiveTema] = useState<TemaKey>("Todos");

  const activeThemeColor = TEMAS.find((t) => t.key === activeTema)?.color ?? "#8A8A96";

  const filteredClusters = useMemo(() => {
    if (activeTema === "Todos") return clusters;
    return clusters.filter((c) => c.theme === activeTema);
  }, [clusters, activeTema]);

  const filteredSignals = useMemo(() => {
    if (activeTema === "Todos") return signals;
    return signals.filter((s) => s.theme === activeTema);
  }, [signals, activeTema]);

  // Signals shown in the feed — cap at 9 for a clean 3-col grid
  const visibleSignals = filteredSignals.slice(0, 9);

  const aggregated = useMemo(() => aggregateDimensions(filteredClusters), [filteredClusters]);
  const hasRadar = Object.keys(aggregated).length > 0;

  return (
    <div id="panel-temas" role="tabpanel" aria-label="Temas e Clusters" className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="mb-1 font-display text-[22px] text-sinal-white">Temas em Alta</h2>
          <p className="text-[13px] text-ash">
            Clusters e sinais agrupados por tema. Selecione um tema para ver clusters e sinais
            filtrados.
          </p>
        </div>
        {filteredClusters.length > 0 && (
          <span className="font-mono text-[12px] text-[#4A4A56]">
            {filteredClusters.length} cluster{filteredClusters.length !== 1 ? "s" : ""}
            {activeTema !== "Todos" ? ` em ${activeTema}` : ""}
          </span>
        )}
      </div>

      {/* Theme filter pills */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tema">
        {TEMAS.map((tema) => {
          const isActive = activeTema === tema.key;
          return (
            <button
              key={tema.key}
              onClick={() => setActiveTema(tema.key)}
              className={[
                "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 font-mono text-[11px] transition-all",
                isActive
                  ? "border-sinal-slate bg-sinal-graphite text-sinal-white"
                  : "border-[rgba(255,255,255,0.06)] text-ash hover:border-sinal-slate hover:text-silver",
              ].join(" ")}
            >
              {tema.key !== "Todos" && (
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full"
                  style={{ backgroundColor: tema.color }}
                  aria-hidden="true"
                />
              )}
              {tema.label}
            </button>
          );
        })}
      </div>

      {/* Clusters grid + radar side-by-side on large screens */}
      {filteredClusters.length > 0 ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_280px]">
          {/* Cluster grid */}
          <div>
            <h3 className="mb-3 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
              Clusters Detectados
            </h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {filteredClusters.map((cluster) => (
                <ClusterCard key={cluster.id} cluster={cluster} />
              ))}
            </div>
          </div>

          {/* Dimension radar — shown only when there are dimension scores */}
          {hasRadar && (
            <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
              <h3 className="mb-1 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
                Dimensoes
              </h3>
              <p className="mb-4 text-[11px] text-[#4A4A56]">
                Media dos scores dos clusters{activeTema !== "Todos" ? ` em ${activeTema}` : ""}.
              </p>
              <DimensionRadar dimensions={aggregated} accentColor={activeThemeColor} />
            </div>
          )}
        </div>
      ) : (
        <div className="rounded-xl border border-sinal-slate bg-sinal-graphite py-10 text-center">
          <p className="mb-1 text-[14px] text-ash">Nenhum cluster encontrado</p>
          <p className="text-[12px] text-[#4A4A56]">
            {activeTema !== "Todos"
              ? `Clusters de "${activeTema}" aparecerao apos a proxima coleta do agente RADAR.`
              : "Clusters aparecerao apos a proxima coleta do agente RADAR."}
          </p>
        </div>
      )}

      {/* Recent signals feed */}
      <div>
        <h3 className="mb-4 font-display text-[18px] text-sinal-white">
          Sinais Recentes
          {activeTema !== "Todos" && (
            <span
              className="ml-2 font-mono text-[13px] font-normal"
              style={{ color: activeThemeColor }}
            >
              {activeTema}
            </span>
          )}
        </h3>

        {visibleSignals.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {visibleSignals.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        ) : (
          <div className="py-12 text-center">
            <p className="mb-1 text-[14px] text-ash">Nenhum sinal encontrado</p>
            <p className="text-[12px] text-[#4A4A56]">
              {activeTema !== "Todos"
                ? `Sinais de "${activeTema}" aparecerao apos a proxima coleta.`
                : "Sinais aparecerao apos a proxima coleta do agente RADAR."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

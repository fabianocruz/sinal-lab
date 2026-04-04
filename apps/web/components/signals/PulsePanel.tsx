"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import type { WeeklyPulse, SignalCluster, SignalStats } from "@/lib/signal";
import { STAGE_COLORS, STAGE_LABELS } from "@/lib/signal";
import Link from "next/link";
import PlatformHeatmap from "@/components/signals/PlatformHeatmap";
import type { PlatformHeatmapRow } from "@/components/signals/PlatformHeatmap";
import ClusterCard from "@/components/signals/ClusterCard";

// ---------------------------------------------------------------------------
// Theme filter constants
// ---------------------------------------------------------------------------

const THEME_OPTIONS = [
  { key: "all", label: "Todos" },
  { key: "AI", label: "AI" },
  { key: "Fintech", label: "Fintech" },
  { key: "AI in Banking", label: "AI in Banking" },
];

const WATCHLIST_KEY = "sinal_watchlist";

interface PulsePanelProps {
  pulse: WeeklyPulse | null;
  clusters: SignalCluster[];
  stats: SignalStats;
}

function EmptyState({ message, sub }: { message: string; sub?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <p className="mb-1 text-[14px] text-ash">{message}</p>
      {sub && <p className="text-[12px] text-[#4A4A56]">{sub}</p>}
    </div>
  );
}

function ThemeRow({
  name,
  score,
  delta,
  stage,
  rank,
}: {
  name: string;
  score: number;
  delta?: number;
  stage: string;
  rank: number;
}) {
  const color = STAGE_COLORS[stage] ?? "#8A8A96";
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);

  return (
    <div className="flex items-center gap-3 py-3 border-b border-[rgba(255,255,255,0.04)] last:border-0">
      <span className="w-4 shrink-0 font-mono text-[11px] text-[#4A4A56] text-right">{rank}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1.5">
          <p className="font-mono text-[13px] text-sinal-white truncate pr-2">{name}</p>
          <div className="flex items-center gap-2 shrink-0">
            {delta != null && delta > 0 && (
              <span className="font-mono text-[11px] text-signal">+{Math.round(delta * 100)}%</span>
            )}
            <span className="font-mono text-[11px]" style={{ color }}>
              {pct}
            </span>
          </div>
        </div>
        <div className="h-[2px] w-full overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${pct}%`, backgroundColor: color }}
          />
        </div>
      </div>
    </div>
  );
}

// Derive PlatformHeatmapRow data from clusters + their top_posts
function buildHeatmapData(clusters: SignalCluster[]): PlatformHeatmapRow[] {
  return clusters.slice(0, 5).map((cluster) => {
    const counts: Record<string, number> = { twitter: 0, reddit: 0, bluesky: 0, rss: 0 };
    cluster.top_posts.forEach((post) => {
      const p = post.platform.toLowerCase();
      if (p in counts) counts[p]++;
    });
    return {
      theme: cluster.name,
      twitter: counts.twitter,
      reddit: counts.reddit,
      bluesky: counts.bluesky,
      rss: counts.rss,
    };
  });
}

// ---------------------------------------------------------------------------
// Watchlist helpers
// ---------------------------------------------------------------------------

function readWatchlist(): Set<string> {
  try {
    const raw = localStorage.getItem(WATCHLIST_KEY);
    if (!raw) return new Set();
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((x): x is string => typeof x === "string"));
  } catch {
    return new Set();
  }
}

function writeWatchlist(slugs: Set<string>): void {
  try {
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify([...slugs]));
  } catch {
    // localStorage may be unavailable (private mode, storage quota, etc.)
  }
}

export default function PulsePanel({ pulse, clusters }: PulsePanelProps) {
  const [activeTheme, setActiveTheme] = useState("all");
  // Start with empty set; populate after mount to avoid SSR/hydration mismatch
  const [watchlist, setWatchlist] = useState<Set<string>>(new Set());
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage after mount
  useEffect(() => {
    setWatchlist(readWatchlist());
    setHydrated(true);
  }, []);

  const handleWatch = useCallback((slug: string) => {
    setWatchlist((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) {
        next.delete(slug);
      } else {
        next.add(slug);
      }
      writeWatchlist(next);
      return next;
    });
  }, []);

  const accelerating = pulse?.accelerating_themes ?? [];
  const emerging = pulse?.emerging_signals ?? [];

  // Filter clusters by selected theme, then sort by signal_count
  const filteredClusters = useMemo(() => {
    if (activeTheme === "all") return clusters;
    return clusters.filter((c) => c.theme?.toLowerCase() === activeTheme.toLowerCase());
  }, [clusters, activeTheme]);

  // Dominant narratives: filtered clusters sorted by signal_count
  const dominant = [...filteredClusters]
    .sort((a, b) => b.signal_count - a.signal_count)
    .slice(0, 5);

  // Clusters currently in watchlist
  const watchedClusters = useMemo(
    () => clusters.filter((c) => watchlist.has(c.slug)),
    [clusters, watchlist],
  );

  return (
    <div id="panel-pulse" role="tabpanel" aria-label="Pulse Geral" className="space-y-6">
      {/* Week badge */}
      {pulse && (
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal" aria-hidden="true" />
          <span className="font-mono text-[11px] uppercase tracking-[1.5px] text-signal">
            Semana {pulse.week_number}/{pulse.year}
          </span>
        </div>
      )}

      {/* Temas Monitorados — watchlist section */}
      {hydrated && (
        <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h3 className="mb-1 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
                Temas Monitorados
              </h3>
              <p className="text-[12px] text-[#4A4A56]">Clusters que voce esta acompanhando</p>
            </div>
            {watchedClusters.length > 0 && (
              <span className="rounded-full bg-[rgba(232,255,89,0.10)] px-2.5 py-[3px] font-mono text-[11px] text-signal">
                {watchedClusters.length}
              </span>
            )}
          </div>

          {watchedClusters.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {watchedClusters.map((cluster) => (
                <ClusterCard
                  key={cluster.id}
                  cluster={cluster}
                  isWatched={true}
                  onWatch={handleWatch}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1}
                stroke="currentColor"
                className="mb-3 h-8 w-8 text-[#4A4A56]"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z"
                />
              </svg>
              <p className="mb-1 text-[14px] text-ash">Nenhum tema monitorado</p>
              <p className="text-[12px] text-[#4A4A56]">
                Clique no marcador nos cards abaixo para acompanhar um tema
              </p>
            </div>
          )}
        </div>
      )}

      {/* Theme filter pills */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tema">
        {THEME_OPTIONS.map((opt) => {
          const isActive = activeTheme === opt.key;
          return (
            <button
              key={opt.key}
              onClick={() => setActiveTheme(opt.key)}
              aria-pressed={isActive}
              className={[
                "rounded-lg border px-3 py-2 font-mono text-[11px] uppercase tracking-[0.8px] transition-all duration-200",
                isActive
                  ? "border-signal bg-[rgba(232,255,89,0.08)] text-signal"
                  : "border-[rgba(255,255,255,0.06)] text-ash hover:text-silver",
              ].join(" ")}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {/* Two-column: accelerating + emerging */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Accelerating themes */}
        <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
          <h3 className="mb-1 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
            Temas Acelerando
          </h3>
          <p className="mb-4 text-[12px] text-[#4A4A56]">
            Clusters com maior crescimento esta semana
          </p>
          {accelerating.length > 0 ? (
            <div>
              {accelerating.slice(0, 5).map((theme, i) => (
                <ThemeRow
                  key={theme.name}
                  name={theme.name}
                  score={theme.score}
                  delta={theme.delta}
                  stage="accelerating"
                  rank={i + 1}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              message="Nenhum dado disponivel"
              sub="Gerado pelo agente RADAR semanalmente."
            />
          )}
        </div>

        {/* Emerging signals */}
        <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
          <h3 className="mb-1 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
            Sinais Emergentes
          </h3>
          <p className="mb-4 text-[12px] text-[#4A4A56]">Temas novos detectados nas ultimas 48h</p>
          {emerging.length > 0 ? (
            <div>
              {emerging.slice(0, 5).map((signal, i) => (
                <ThemeRow
                  key={signal.name}
                  name={signal.name}
                  score={signal.score}
                  stage="emerging"
                  rank={i + 1}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              message="Nenhum dado disponivel"
              sub="Gerado pelo agente RADAR semanalmente."
            />
          )}
        </div>
      </div>

      {/* Cluster card grid — all filtered clusters with watchlist toggles */}
      {filteredClusters.length > 0 && (
        <div>
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h3 className="mb-1 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
                Clusters de Tendencias
              </h3>
              <p className="text-[12px] text-[#4A4A56]">
                {filteredClusters.length} cluster{filteredClusters.length !== 1 ? "s" : ""}{" "}
                detectado{filteredClusters.length !== 1 ? "s" : ""} esta semana
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredClusters.map((cluster) => (
              <ClusterCard
                key={cluster.id}
                cluster={cluster}
                isWatched={watchlist.has(cluster.slug)}
                onWatch={handleWatch}
              />
            ))}
          </div>
        </div>
      )}

      {/* Dominant narratives */}
      <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
        <h3 className="mb-1 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
          Narrativas Dominantes
        </h3>
        <p className="mb-4 text-[12px] text-[#4A4A56]">Clusters com maior volume de sinais</p>
        {dominant.length > 0 ? (
          <div className="flex flex-wrap gap-3">
            {dominant.map((cluster) => {
              const stageColor = STAGE_COLORS[cluster.narrative_stage] ?? "#8A8A96";
              const stageLabel = STAGE_LABELS[cluster.narrative_stage] ?? cluster.narrative_stage;
              return (
                <Link
                  key={cluster.id}
                  href={`/signals/cluster/${cluster.slug}`}
                  className="flex items-center gap-2.5 rounded-lg border border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.03)] px-4 py-2.5 transition-all hover:border-[rgba(255,255,255,0.12)] hover:bg-[rgba(255,255,255,0.05)]"
                >
                  <span className="font-mono text-[13px] text-sinal-white">{cluster.name}</span>
                  <span
                    className="rounded px-1.5 py-[2px] font-mono text-[9px] uppercase tracking-[0.5px]"
                    style={{ color: stageColor, backgroundColor: `${stageColor}14` }}
                  >
                    {stageLabel}
                  </span>
                  <span className="font-mono text-[11px] text-ash">
                    {cluster.signal_count.toLocaleString("pt-BR")}
                  </span>
                </Link>
              );
            })}
          </div>
        ) : (
          <EmptyState
            message="Nenhum cluster disponivel"
            sub="Os clusters sao gerados pelo agente RADAR semanalmente."
          />
        )}
      </div>

      {/* Platform heatmap */}
      <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
        <h3 className="mb-1 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
          Heatmap por Plataforma
        </h3>
        <p className="mb-4 text-[12px] text-[#4A4A56]">Volume de sinais por tema e plataforma</p>
        {dominant.length > 0 ? (
          <PlatformHeatmap data={buildHeatmapData(dominant)} />
        ) : (
          <EmptyState
            message="Sem dados de plataforma"
            sub="O heatmap aparece apos coleta de sinais."
          />
        )}
      </div>
    </div>
  );
}

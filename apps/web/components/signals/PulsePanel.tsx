import type { WeeklyPulse, SignalCluster, SignalStats } from "@/lib/signal";
import { STAGE_COLORS, STAGE_LABELS, PLATFORM_LABELS } from "@/lib/signal";
import Link from "next/link";

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

function PlatformHeatmap({ clusters, stats }: { clusters: SignalCluster[]; stats: SignalStats }) {
  const platforms = Object.keys(stats.platforms).filter((p) => stats.platforms[p] > 0);
  // Use top 5 clusters by signal count for the heatmap rows
  const topClusters = clusters.slice(0, 5);

  if (platforms.length === 0 || topClusters.length === 0) {
    return (
      <EmptyState
        message="Sem dados de plataforma"
        sub="O heatmap aparece apos coleta de sinais."
      />
    );
  }

  // Max signal count for normalization
  const maxSignals = Math.max(...topClusters.map((c) => c.signal_count), 1);

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[400px] text-left">
        <thead>
          <tr>
            <th className="pb-2 pr-4 font-mono text-[10px] uppercase tracking-[1px] text-[#4A4A56] w-[160px]">
              Tema
            </th>
            {platforms.slice(0, 5).map((p) => (
              <th
                key={p}
                className="pb-2 px-2 font-mono text-[10px] uppercase tracking-[1px] text-[#4A4A56] text-center"
              >
                {PLATFORM_LABELS[p] ?? p}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {topClusters.map((cluster) => {
            const intensity = cluster.signal_count / maxSignals;
            return (
              <tr key={cluster.id}>
                <td className="py-1.5 pr-4">
                  <Link
                    href={`/signals/cluster/${cluster.slug}`}
                    className="font-mono text-[12px] text-silver hover:text-sinal-white transition-colors truncate block max-w-[150px]"
                  >
                    {cluster.name}
                  </Link>
                </td>
                {platforms.slice(0, 5).map((p) => {
                  // Use cluster top_posts to count per platform
                  const count = cluster.top_posts.filter((post) => post.platform === p).length;
                  const cellIntensity = count > 0 ? 0.3 + intensity * 0.5 : 0;
                  return (
                    <td key={p} className="py-1.5 px-2 text-center">
                      <div
                        className="mx-auto h-6 w-6 rounded flex items-center justify-center"
                        style={{
                          backgroundColor: `rgba(232,255,89,${cellIntensity})`,
                        }}
                        title={`${count} posts`}
                      >
                        {count > 0 && (
                          <span className="font-mono text-[10px] text-sinal-white">{count}</span>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function PulsePanel({ pulse, clusters, stats }: PulsePanelProps) {
  const accelerating = pulse?.accelerating_themes ?? [];
  const emerging = pulse?.emerging_signals ?? [];

  // Dominant narratives: clusters sorted by signal_count
  const dominant = [...clusters].sort((a, b) => b.signal_count - a.signal_count).slice(0, 5);

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
        <PlatformHeatmap clusters={dominant} stats={stats} />
      </div>
    </div>
  );
}

import Link from "next/link";
import type { SignalCluster } from "@/lib/signal";
import { STAGE_COLORS, STAGE_LABELS } from "@/lib/signal";

interface TrendingSidebarProps {
  clusters: SignalCluster[];
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);
  return (
    <div className="mt-1.5 h-[3px] w-full overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
      <div
        className="h-full rounded-full bg-signal"
        style={{ width: `${pct}%` }}
        aria-hidden="true"
      />
    </div>
  );
}

export default function TrendingSidebar({ clusters }: TrendingSidebarProps) {
  // Sort by composite_score descending, take top 5
  const top = [...clusters].sort((a, b) => b.composite_score - a.composite_score).slice(0, 5);

  if (top.length === 0) {
    return (
      <aside
        aria-label="Clusters em tendencia"
        className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5"
      >
        <p className="font-mono text-[11px] text-[#4A4A56]">
          Nenhum cluster disponivel no momento.
        </p>
      </aside>
    );
  }

  return (
    <aside aria-label="Clusters em tendencia">
      {/* Header */}
      <div className="mb-4 flex items-center gap-2">
        <span
          className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-agent-radar"
          aria-hidden="true"
        />
        <span className="font-mono text-[10px] uppercase tracking-[2px] text-ash">Tendencias</span>
      </div>

      <ol className="space-y-3" aria-label="Top clusters por score">
        {top.map((cluster, idx) => {
          const stageColor = STAGE_COLORS[cluster.narrative_stage] ?? "#9A9AA8";
          const stageLabel = STAGE_LABELS[cluster.narrative_stage] ?? cluster.narrative_stage;

          return (
            <li key={cluster.id}>
              <Link
                href={`/signals/cluster/${cluster.slug}`}
                className="group block rounded-xl border border-sinal-slate bg-sinal-graphite p-4 transition-colors hover:border-[rgba(255,255,255,0.12)] hover:bg-[rgba(255,255,255,0.02)]"
              >
                {/* Rank + stage */}
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="font-mono text-[10px] text-[#4A4A56]">#{idx + 1}</span>
                  <span
                    className="rounded px-1.5 py-[2px] font-mono text-[9px] uppercase tracking-[1px]"
                    style={{ color: stageColor, backgroundColor: `${stageColor}18` }}
                  >
                    {stageLabel}
                  </span>
                </div>

                {/* Cluster name */}
                <p className="mb-1 text-[13px] font-semibold leading-[1.4] text-silver transition-colors group-hover:text-sinal-white">
                  {cluster.name}
                </p>

                {/* Score bar */}
                <ScoreBar score={cluster.composite_score} />

                {/* Meta: score + signal count */}
                <div className="mt-2 flex items-center justify-between">
                  <span className="font-mono text-[10px] text-[#4A4A56]">
                    Score{" "}
                    <span className="text-ash">{(cluster.composite_score * 100).toFixed(0)}</span>
                  </span>
                  <span className="font-mono text-[10px] text-[#4A4A56]">
                    <span className="text-ash">{cluster.signal_count}</span> sinais
                  </span>
                </div>
              </Link>
            </li>
          );
        })}
      </ol>

      {/* Footer link */}
      <div className="mt-4">
        <Link
          href="/signals?tab=pulse"
          className="block text-center font-mono text-[11px] text-ash transition-colors hover:text-sinal-white"
        >
          Ver todos os clusters &rarr;
        </Link>
      </div>
    </aside>
  );
}

"use client";

import Link from "next/link";
import type { SignalCluster } from "@/lib/signal";
import { STAGE_COLORS, STAGE_LABELS, PLATFORM_COLORS } from "@/lib/signal";
import WatchlistButton from "@/components/signals/WatchlistButton";

interface ClusterCardProps {
  cluster: SignalCluster;
  isWatched?: boolean;
  onWatch?: (slug: string) => void;
}

function scoreBar(score: number) {
  // score is 0–1; render as a narrow progress bar
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);
  return (
    <div className="h-[3px] w-full overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
      <div
        className="h-full rounded-full bg-signal transition-all duration-500"
        style={{ width: `${pct}%` }}
        aria-label={`Score: ${pct}%`}
      />
    </div>
  );
}

export default function ClusterCard({ cluster, isWatched = false, onWatch }: ClusterCardProps) {
  const stageColor = STAGE_COLORS[cluster.narrative_stage] ?? "#8A8A96";
  const stageLabel = STAGE_LABELS[cluster.narrative_stage] ?? cluster.narrative_stage;

  // Unique platforms from top_posts
  const platforms = [...new Set(cluster.top_posts.map((p) => p.platform))].slice(0, 4);

  return (
    <div className="group relative">
      <Link
        href={`/signals/cluster/${cluster.slug}`}
        className="block overflow-hidden rounded-xl border border-sinal-slate bg-sinal-graphite transition-all duration-300 hover:-translate-y-[2px] hover:border-[rgba(255,255,255,0.10)] hover:shadow-[0_8px_32px_rgba(0,0,0,0.3)]"
        aria-label={`Ver cluster: ${cluster.name}`}
      >
        {/* Top accent bar */}
        <div
          className="h-[2px] opacity-40 transition-opacity duration-300 group-hover:opacity-100"
          style={{ background: `linear-gradient(90deg, ${stageColor}, transparent)` }}
          aria-hidden="true"
        />

        <div className="flex flex-col px-5 pb-4 pt-5">
          {/* Header */}
          <div className="mb-3 flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h2 className="mb-1 truncate font-display text-[17px] leading-[1.2] text-sinal-white">
                {cluster.name}
              </h2>
              <span className="font-mono text-[11px] uppercase tracking-[0.5px] text-ash">
                {cluster.theme}
                {cluster.sub_theme ? ` / ${cluster.sub_theme}` : ""}
              </span>
            </div>

            <div className="flex shrink-0 items-center gap-1">
              {/* Stage badge */}
              <span
                className="rounded px-2 py-[3px] font-mono text-[9px] font-semibold uppercase tracking-[1px]"
                style={{
                  color: stageColor,
                  backgroundColor: `${stageColor}14`,
                }}
              >
                {stageLabel}
              </span>

              {/* Watchlist toggle — only rendered when caller passes onWatch */}
              {onWatch && (
                <WatchlistButton slug={cluster.slug} isWatched={isWatched} onToggle={onWatch} />
              )}
            </div>
          </div>

          {/* Description */}
          {cluster.description && (
            <p className="mb-4 line-clamp-2 text-[13px] leading-[1.5] text-silver">
              {cluster.description}
            </p>
          )}

          {/* Composite score bar */}
          <div className="mb-4">{scoreBar(cluster.composite_score)}</div>

          {/* Bottom stats */}
          <div className="mt-auto flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] pt-3">
            {/* Signal count */}
            <div className="flex flex-col items-start">
              <span className="font-mono text-[14px] font-semibold leading-none text-sinal-white">
                {cluster.signal_count.toLocaleString("pt-BR")}
              </span>
              <span className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.5px] text-[#4A4A56]">
                Sinais
              </span>
            </div>

            {/* Score */}
            <div className="flex flex-col items-end">
              <span
                className="font-mono text-[14px] font-semibold leading-none"
                style={{ color: stageColor }}
              >
                {Math.round(cluster.composite_score * 100)}
              </span>
              <span className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.5px] text-[#4A4A56]">
                Score
              </span>
            </div>

            {/* Platform dots */}
            {platforms.length > 0 && (
              <div className="flex items-center gap-1">
                {platforms.map((platform) => (
                  <span
                    key={platform}
                    className="inline-block h-[8px] w-[8px] rounded-full"
                    style={{ backgroundColor: PLATFORM_COLORS[platform] ?? "#4A4A56" }}
                    title={platform}
                    aria-label={platform}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </Link>
    </div>
  );
}

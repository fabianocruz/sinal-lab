import Link from "next/link";
import type { Signal } from "@/lib/signal";
import { PLATFORM_COLORS, PLATFORM_LABELS } from "@/lib/signal";

interface SignalCardProps {
  signal: Signal;
}

function relativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

function formatMetric(value: number | undefined): string {
  if (value == null || value === 0) return "0";
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return String(value);
}

export default function SignalCard({ signal }: SignalCardProps) {
  const platformColor = PLATFORM_COLORS[signal.platform] ?? "#4A4A56";
  const platformLabel = PLATFORM_LABELS[signal.platform] ?? signal.platform;
  const initial = (signal.author_display_name || signal.author_handle || "?")
    .charAt(0)
    .toUpperCase();
  const timeAgo = relativeTime(signal.published_at);

  return (
    <article className="overflow-hidden rounded-xl border border-sinal-slate bg-sinal-graphite transition-all duration-300 hover:border-[rgba(255,255,255,0.10)]">
      {/* Platform accent */}
      <div
        className="h-[2px] opacity-30"
        style={{ background: `linear-gradient(90deg, ${platformColor}, transparent)` }}
        aria-hidden="true"
      />

      <div className="px-4 pb-4 pt-4">
        {/* Header row */}
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            {/* Avatar initial */}
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-mono text-[12px] font-semibold"
              style={{
                backgroundColor: `${platformColor}18`,
                color: platformColor,
              }}
              aria-hidden="true"
            >
              {initial}
            </div>

            {/* Author info */}
            <div className="min-w-0">
              <p className="truncate font-mono text-[13px] font-semibold text-sinal-white">
                {signal.author_display_name || signal.author_handle}
              </p>
              <p className="font-mono text-[11px] text-ash">@{signal.author_handle}</p>
            </div>
          </div>

          {/* Platform + time */}
          <div className="flex shrink-0 flex-col items-end gap-1">
            <span
              className="rounded px-1.5 py-[2px] font-mono text-[9px] font-semibold uppercase tracking-[1px]"
              style={{ color: platformColor, backgroundColor: `${platformColor}14` }}
            >
              {platformLabel}
            </span>
            <span className="font-mono text-[11px] text-[#4A4A56]">{timeAgo}</span>
          </div>
        </div>

        {/* Post text */}
        <p className="mb-3 line-clamp-3 text-[13px] leading-[1.55] text-silver">{signal.text}</p>

        {/* Footer: metrics + link */}
        <div className="flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] pt-3">
          {/* Metrics */}
          <div className="flex items-center gap-4">
            {signal.metrics.likes != null && (
              <span className="font-mono text-[11px] text-ash">
                <span className="text-silver">{formatMetric(signal.metrics.likes)}</span> likes
              </span>
            )}
            {signal.metrics.replies != null && (
              <span className="font-mono text-[11px] text-ash">
                <span className="text-silver">{formatMetric(signal.metrics.replies)}</span> replies
              </span>
            )}
            {signal.metrics.reposts != null && (
              <span className="font-mono text-[11px] text-ash">
                <span className="text-silver">{formatMetric(signal.metrics.reposts)}</span> reposts
              </span>
            )}
          </div>

          {/* External link */}
          <Link
            href={signal.post_url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[11px] text-ash transition-colors hover:text-sinal-white"
            aria-label={`Ver post de ${signal.author_handle} no ${platformLabel}`}
          >
            Ver post &rarr;
          </Link>
        </div>
      </div>
    </article>
  );
}

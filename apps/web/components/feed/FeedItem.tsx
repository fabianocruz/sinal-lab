import type { Signal } from "@/lib/signal";

// ---------------------------------------------------------------------------
// Platform config
// ---------------------------------------------------------------------------

interface PlatformConfig {
  icon: string;
  color: string;
  label: string;
}

const PLATFORM_CONFIG: Record<string, PlatformConfig> = {
  twitter: { icon: "𝕏", color: "#1DA1F2", label: "Twitter/X" },
  reddit: { icon: "R", color: "#FF4500", label: "Reddit" },
  bluesky: { icon: "B", color: "#0085FF", label: "Bluesky" },
  youtube: { icon: "Y", color: "#FF0000", label: "YouTube" },
  linkedin: { icon: "in", color: "#0A66C2", label: "LinkedIn" },
  polymarket: { icon: "P", color: "#4ADE80", label: "Polymarket" },
  rss: { icon: "R", color: "#EE802F", label: "Newsletter" },
};

const FALLBACK_PLATFORM: PlatformConfig = { icon: "?", color: "#9A9AA8", label: "Fonte" };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function relativeTime(dateStr: string): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "agora";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "ontem";
  return `${days}d`;
}

export function formatMetric(n: number | undefined): string {
  if (n == null || n === 0) return "0";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface FeedItemProps {
  signal: Signal;
}

export default function FeedItem({ signal }: FeedItemProps) {
  const platform = PLATFORM_CONFIG[signal.platform] ?? FALLBACK_PLATFORM;
  const initial = (signal.author_display_name || signal.author_handle || "?")
    .charAt(0)
    .toUpperCase();

  const hasMetrics =
    (signal.metrics?.likes ?? 0) > 0 ||
    (signal.metrics?.replies ?? 0) > 0 ||
    (signal.metrics?.reposts ?? 0) > 0;

  return (
    <article
      className="border-b border-[rgba(255,255,255,0.05)] py-6 transition-colors hover:bg-[rgba(255,255,255,0.01)]"
      aria-label={`Post de ${signal.author_display_name || signal.author_handle} em ${platform.label}`}
    >
      {/* Platform + time header */}
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* Platform badge */}
          <span
            className="rounded px-1.5 py-[2px] font-mono text-[9px] font-semibold uppercase tracking-[1px]"
            style={{ color: platform.color, backgroundColor: `${platform.color}18` }}
          >
            {platform.icon} {platform.label}
          </span>

          {/* Theme badge */}
          {signal.theme && (
            <span className="rounded bg-[rgba(255,255,255,0.05)] px-2 py-[2px] font-mono text-[9px] uppercase tracking-[1px] text-ash">
              {signal.theme}
            </span>
          )}

          {/* Sub-theme badge */}
          {signal.sub_theme && signal.sub_theme !== signal.theme && (
            <span className="hidden rounded bg-[rgba(255,255,255,0.03)] px-2 py-[2px] font-mono text-[9px] uppercase tracking-[1px] text-[#4A4A56] sm:inline">
              {signal.sub_theme}
            </span>
          )}
        </div>

        <time
          dateTime={signal.published_at}
          className="shrink-0 font-mono text-[11px] text-[#4A4A56]"
        >
          {relativeTime(signal.published_at)}
        </time>
      </div>

      {/* Author row */}
      <div className="mb-3 flex items-center gap-2.5">
        {/* Avatar initial */}
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-mono text-[13px] font-semibold"
          style={{
            backgroundColor: `${platform.color}18`,
            color: platform.color,
          }}
          aria-hidden="true"
        >
          {initial}
        </div>

        {/* Name + handle */}
        <div className="min-w-0">
          <span className="text-[14px] font-semibold text-sinal-white">
            {signal.author_display_name || signal.author_handle}
          </span>
          {signal.author_handle && (
            <span className="ml-2 font-mono text-[12px] text-ash">@{signal.author_handle}</span>
          )}
        </div>
      </div>

      {/* Post text — full, preserved whitespace */}
      <p className="mb-4 whitespace-pre-line text-[15px] leading-[1.7] text-silver">
        {signal.text}
      </p>

      {/* Footer: metrics + link */}
      <div className="flex flex-wrap items-center gap-4">
        {hasMetrics && (
          <div className="flex items-center gap-4">
            {(signal.metrics?.likes ?? 0) > 0 && (
              <span className="font-mono text-[11px] text-ash">
                <span className="mr-1" aria-hidden="true">
                  ♡
                </span>
                <span className="text-silver">{formatMetric(signal.metrics.likes)}</span>
              </span>
            )}
            {(signal.metrics?.replies ?? 0) > 0 && (
              <span className="font-mono text-[11px] text-ash">
                <span className="mr-1" aria-hidden="true">
                  ↩
                </span>
                <span className="text-silver">{formatMetric(signal.metrics.replies)}</span>
              </span>
            )}
            {(signal.metrics?.reposts ?? 0) > 0 && (
              <span className="font-mono text-[11px] text-ash">
                <span className="mr-1" aria-hidden="true">
                  ↻
                </span>
                <span className="text-silver">{formatMetric(signal.metrics.reposts)}</span>
              </span>
            )}
          </div>
        )}

        {signal.post_url && (
          <a
            href={signal.post_url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto font-mono text-[11px] text-ash transition-colors hover:text-sinal-white"
            aria-label={`Ver post original de ${signal.author_handle} em ${platform.label}`}
          >
            Ver original &rarr;
          </a>
        )}
      </div>
    </article>
  );
}

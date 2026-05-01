import type { CuratedFeedItem } from "@/lib/signal";
import { THEME_COLORS } from "@/lib/signal";
import FeedItemThumbnail from "./FeedItemThumbnail";

const FALLBACK_CATEGORY_COLOR = "#9A9AA8";

// ---------------------------------------------------------------------------
// Platform config
// ---------------------------------------------------------------------------

interface PlatformConfig {
  icon: string;
  label: string;
}

const PLATFORM_CONFIG: Record<string, PlatformConfig> = {
  twitter: { icon: "𝕏", label: "Twitter/X" },
  reddit: { icon: "⬡", label: "Reddit" },
  bluesky: { icon: "◈", label: "Bluesky" },
  youtube: { icon: "▶", label: "YouTube" },
  linkedin: { icon: "in", label: "LinkedIn" },
  polymarket: { icon: "◆", label: "Polymarket" },
  rss: { icon: "◉", label: "Newsletter" },
  web: { icon: "◎", label: "Web" },
  hackernews: { icon: "Y", label: "Hacker News" },
  tiktok: { icon: "♪", label: "TikTok" },
};

const FALLBACK_PLATFORM: PlatformConfig = { icon: "◎", label: "Web" };

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
  item: CuratedFeedItem;
}

export default function FeedItem({ item }: FeedItemProps) {
  const platformCfg = PLATFORM_CONFIG[item.platform] ?? FALLBACK_PLATFORM;
  const categoryColor = THEME_COLORS[item.category] ?? FALLBACK_CATEGORY_COLOR;

  const hasThumbnail = Boolean(item.thumbnail_url);
  const hasYouTubeEmbed = item.video_embed?.platform === "youtube";
  const hasLikes = (item.metrics?.likes ?? 0) > 0;

  return (
    <article
      className="border-b border-[rgba(255,255,255,0.04)] py-6 transition-colors hover:bg-[rgba(255,255,255,0.01)]"
      aria-label={`${item.editorial_headline} — ${item.author_display_name || item.author_handle}`}
    >
      <div className="flex gap-4">
        {/* Thumbnail — left side, only when available. Client component
            so we can hide the slot when the image 403s (Reddit hotlink,
            dead CDN URLs, etc.) instead of leaving a hollow rectangle. */}
        {hasThumbnail && <FeedItemThumbnail src={item.thumbnail_url!} href={item.original_url} />}

        <div className="min-w-0 flex-1">
          {/* Category + platform + time */}
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span
              className="font-mono text-[11px] uppercase tracking-wider"
              style={{ color: categoryColor }}
            >
              {item.category}
            </span>
            <span className="font-mono text-[10px] text-ash">
              {platformCfg.icon} {platformCfg.label} &middot;{" "}
              <time dateTime={item.curated_at}>{relativeTime(item.curated_at)}</time>
            </span>
          </div>

          {/* Editorial headline */}
          <h3 className="mb-1 font-display text-[18px] leading-[1.3] text-sinal-white">
            <a
              href={item.original_url}
              target="_blank"
              rel="noopener noreferrer"
              className="transition-colors hover:text-signal"
            >
              {item.editorial_headline}
            </a>
          </h3>

          {/* Editorial context */}
          {item.editorial_context && (
            <p className="mb-2 text-[14px] leading-[1.6] text-silver">{item.editorial_context}</p>
          )}

          {/* Author + metrics row */}
          <div className="flex flex-wrap items-center gap-3 text-[12px] text-ash">
            {(item.author_display_name || item.author_handle) && (
              <span>{item.author_display_name || `@${item.author_handle}`}</span>
            )}
            {hasLikes && (
              <span aria-label={`${item.metrics!.likes} likes`}>
                &#9825; {formatMetric(item.metrics!.likes)}
              </span>
            )}
            <a
              href={item.original_url}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto font-mono text-[11px] transition-colors hover:text-sinal-white"
            >
              Ver original &rarr;
            </a>
          </div>
        </div>
      </div>

      {/* YouTube embed — rendered below the card row */}
      {hasYouTubeEmbed && (
        <div className="mt-4 aspect-video overflow-hidden rounded-lg">
          <iframe
            src={item.video_embed!.embed_url}
            title={item.editorial_headline}
            className="h-full w-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      )}
    </article>
  );
}

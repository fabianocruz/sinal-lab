"use client";

import { useState, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Voice, Signal } from "@/lib/signal";
import { PLATFORM_COLORS, PLATFORM_LABELS, VOICE_TYPE_LABELS } from "@/lib/signal";
import type { Persona } from "@/components/signals/PersonaSelector";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RecentSignal {
  text: string;
  url: string;
  platform: string;
  published_at: string;
  metrics: Record<string, number>;
}

interface EnrichedVoice extends Voice {
  recent_signals: RecentSignal[];
  recent_signal_count: number;
}

interface VoicesPanelProps {
  voices: Voice[];
  recentSignals: Signal[];
  total: number;
  activeType: string;
  persona?: Persona;
}

// ---------------------------------------------------------------------------
// Persona-based sort priority
// ---------------------------------------------------------------------------

// Returns a priority weight: lower = float to top (stable sort keeps relative order)
function personaSortWeight(accountType: string | null, persona: Persona): number {
  if (persona === "all") return 0;
  const type = accountType ?? "";

  if (persona === "vc") {
    if (type === "vc" || type === "angel") return 0;
    if (type === "executive") return 1;
    return 2;
  }

  if (persona === "cto") {
    if (type === "executive") return 0;
    if (type === "founder") return 1;
    if (type === "thought_leader") return 2;
    return 3;
  }

  if (persona === "founder") {
    if (type === "founder") return 0;
    if (type === "executive") return 1;
    return 2;
  }

  return 0;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TYPE_OPTIONS = [
  { key: "all", label: "Todos" },
  { key: "founder", label: VOICE_TYPE_LABELS.founder },
  { key: "vc", label: VOICE_TYPE_LABELS.vc },
  { key: "executive", label: VOICE_TYPE_LABELS.executive },
  { key: "thought_leader", label: VOICE_TYPE_LABELS.thought_leader },
  { key: "company", label: VOICE_TYPE_LABELS.company },
];

const PLATFORM_OPTIONS = [
  { key: "all", label: "Todas" },
  { key: "twitter", label: "Twitter/X" },
  { key: "linkedin", label: "LinkedIn" },
  { key: "bluesky", label: "Bluesky" },
  { key: "reddit", label: "Reddit" },
];

// Maps voice sector_tags to signal themes so that e.g. a "vc" voice
// gets matched to "fintech" signals and a "developer" voice to "ai" signals.
const SECTOR_TAG_TO_THEME: Record<string, string> = {
  fintech: "fintech",
  ai: "ai",
  "artificial intelligence": "ai",
  "machine learning": "ai",
  banking: "ai in banking",
  payments: "fintech",
  crypto: "fintech",
  blockchain: "fintech",
  investor: "fintech",
  vc: "fintech",
  founder: "ai",
  developer: "ai",
  infrastructure: "ai",
};

// Colors keyed by account_type for avatar backgrounds
const TYPE_COLORS: Record<string, string> = {
  founder: "#59FFB4",
  vc: "#E8FF59",
  executive: "#FF8A59",
  thought_leader: "#B59FFF",
  company: "#59D4FF",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getAvatarColor(voice: Voice): string {
  return TYPE_COLORS[voice.account_type ?? ""] ?? "#4A4A56";
}

function buildBio(voice: Voice): string | null {
  if (voice.bio) return voice.bio;
  const meta = voice.metadata_ as Record<string, string> | null;
  if (!meta) return null;
  const parts: string[] = [];
  if (meta["Primary Job Title"]) parts.push(meta["Primary Job Title"]);
  if (meta["Organization"]) parts.push(meta["Organization"]);
  return parts.length > 0 ? parts.join(" at ") : null;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
  });
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + "...";
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TypeFilter({ activeType }: { activeType: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function handleSelect(type: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (type === "all") {
      params.delete("type");
    } else {
      params.set("type", type);
    }
    params.delete("page");
    router.push(`/signals?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tipo de conta">
      {TYPE_OPTIONS.map((opt) => {
        const isActive = activeType === opt.key;
        return (
          <button
            key={opt.key}
            onClick={() => handleSelect(opt.key)}
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
  );
}

function PlatformFilter({
  activePlatform,
  onChange,
}: {
  activePlatform: string;
  onChange: (value: string) => void; // eslint-disable-line no-unused-vars
}) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por plataforma">
      {PLATFORM_OPTIONS.map((opt) => {
        const color = PLATFORM_COLORS[opt.key] ?? "#E8FF59";
        const isActive = activePlatform === opt.key;
        return (
          <button
            key={opt.key}
            onClick={() => onChange(opt.key)}
            aria-pressed={isActive}
            className={[
              "rounded-lg border px-3 py-2 font-mono text-[11px] uppercase tracking-[0.8px] transition-all duration-200",
              isActive
                ? "border-[rgba(255,255,255,0.15)] bg-[rgba(255,255,255,0.05)] text-sinal-white"
                : "border-[rgba(255,255,255,0.06)] text-ash hover:text-silver",
            ].join(" ")}
            style={isActive ? { borderColor: `${color}40`, color } : {}}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function SignalPost({ post }: { post: RecentSignal }) {
  const totalEngagement =
    (post.metrics.likes ?? 0) + (post.metrics.reposts ?? 0) + (post.metrics.replies ?? 0);

  return (
    <a
      href={post.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-lg border border-[rgba(255,255,255,0.04)] bg-[rgba(255,255,255,0.02)] p-3 transition-all duration-200 hover:border-[rgba(255,255,255,0.10)] hover:bg-[rgba(255,255,255,0.04)]"
    >
      <p className="mb-2 text-[12px] leading-[1.5] text-ash group-hover:text-silver transition-colors">
        {truncate(post.text, 120)}
      </p>
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-[#4A4A56]">
          {formatDate(post.published_at)}
        </span>
        {totalEngagement > 0 && (
          <span className="font-mono text-[10px] text-[#4A4A56]">
            {formatNumber(totalEngagement)} engajamentos
          </span>
        )}
      </div>
    </a>
  );
}

function VoiceCard({ voice }: { voice: EnrichedVoice }) {
  const platformColor = PLATFORM_COLORS[voice.platform] ?? "#4A4A56";
  const platformLabel = PLATFORM_LABELS[voice.platform] ?? voice.platform;
  const avatarColor = getAvatarColor(voice);
  const displayName = voice.display_name || voice.handle;
  const initial = displayName.charAt(0).toUpperCase();
  const authorityPct = Math.round(voice.authority_score * 100);
  const bio = buildBio(voice);
  const accountTypeLabel = voice.account_type
    ? (VOICE_TYPE_LABELS[voice.account_type] ?? voice.account_type)
    : null;
  const recentPosts = voice.recent_signals.slice(0, 2);

  return (
    <article className="flex flex-col rounded-xl border border-sinal-slate bg-sinal-graphite transition-all duration-300 hover:border-[rgba(255,255,255,0.10)]">
      {/* Platform accent bar */}
      <div
        className="h-[2px] w-full rounded-t-xl opacity-30"
        style={{ background: `linear-gradient(90deg, ${platformColor}, transparent)` }}
        aria-hidden="true"
      />

      <div className="flex flex-col p-4">
        {/* Header row */}
        <div className="mb-3 flex items-start gap-3">
          {/* Avatar */}
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-mono text-[14px] font-semibold"
            style={{ backgroundColor: `${avatarColor}18`, color: avatarColor }}
            aria-hidden="true"
          >
            {initial}
          </div>

          {/* Name + handle */}
          <div className="min-w-0 flex-1">
            {voice.profile_url ? (
              <a
                href={voice.profile_url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-1"
              >
                <span className="truncate font-mono text-[13px] font-semibold text-sinal-white transition-colors group-hover:text-signal">
                  {displayName}
                </span>
                <svg
                  className="h-3 w-3 shrink-0 text-[#4A4A56] transition-colors group-hover:text-signal"
                  viewBox="0 0 12 12"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M2.5 9.5L9.5 2.5M9.5 2.5H5.5M9.5 2.5V6.5"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </a>
            ) : (
              <p className="truncate font-mono text-[13px] font-semibold text-sinal-white">
                {displayName}
              </p>
            )}
            <p className="font-mono text-[11px] text-ash">@{voice.handle}</p>
          </div>

          {/* Platform badge */}
          <span
            className="shrink-0 rounded px-1.5 py-[2px] font-mono text-[9px] font-semibold uppercase tracking-[0.8px]"
            style={{ color: platformColor, backgroundColor: `${platformColor}14` }}
          >
            {platformLabel}
          </span>
        </div>

        {/* Bio */}
        {bio && <p className="mb-3 line-clamp-2 text-[12px] leading-[1.5] text-ash">{bio}</p>}

        {/* Badges row */}
        <div className="mb-3 flex flex-wrap gap-1.5">
          {accountTypeLabel && (
            <span
              className="rounded px-2 py-[3px] font-mono text-[10px] font-semibold uppercase tracking-[0.6px]"
              style={{ color: avatarColor, backgroundColor: `${avatarColor}14` }}
            >
              {accountTypeLabel}
            </span>
          )}
          {voice.sector_tags?.slice(0, 2).map((tag) => (
            <span
              key={tag}
              className="rounded border border-[rgba(255,255,255,0.06)] px-2 py-[3px] font-mono text-[10px] text-[#4A4A56]"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Authority score */}
        <div className="mb-4">
          <div className="mb-1 flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-[0.8px] text-[#4A4A56]">
              Autoridade
            </span>
            <div className="flex items-center gap-2">
              {voice.follower_count != null && (
                <span className="font-mono text-[10px] text-[#4A4A56]">
                  {formatNumber(voice.follower_count)} seguidores
                </span>
              )}
              <span className="font-mono text-[11px] text-signal">{authorityPct}</span>
            </div>
          </div>
          <div className="h-[2px] w-full overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
            <div
              className="h-full rounded-full bg-signal transition-all duration-500"
              style={{ width: `${authorityPct}%` }}
            />
          </div>
        </div>

        {/* Recent posts */}
        {recentPosts.length > 0 ? (
          <div className="space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.8px] text-[#4A4A56]">
              Posts recentes
            </p>
            {recentPosts.map((post, i) => (
              <SignalPost key={i} post={post} />
            ))}
          </div>
        ) : (
          <div className="mt-auto border-t border-[rgba(255,255,255,0.06)] pt-3">
            <span className="font-mono text-[11px] text-ash">
              <span className="text-sinal-white">{voice.recent_signal_count}</span> sinais recentes
            </span>
          </div>
        )}
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const VOICES_PER_PAGE = 24;

export default function VoicesPanel({
  voices,
  recentSignals,
  total,
  activeType,
  persona = "all",
}: VoicesPanelProps) {
  const [search, setSearch] = useState("");
  const [activePlatform, setActivePlatform] = useState("all");
  const [page, setPage] = useState(1);

  // Reset to first page whenever filters change
  function handleSearch(value: string) {
    setSearch(value);
    setPage(1);
  }
  function handlePlatformChange(value: string) {
    setActivePlatform(value);
    setPage(1);
  }

  // Build lookup structures from recentSignals
  // Primary key: author_handle (exact match)
  // Secondary: author_display_name (case-insensitive containment)
  // Tertiary: theme-based (signal.theme matches voice.sector_tags)
  const signalsByHandle = useMemo(() => {
    const map = new Map<string, Signal[]>();
    for (const signal of recentSignals) {
      if (!signal.author_handle) continue;
      const handle = signal.author_handle.toLowerCase();
      if (!map.has(handle)) map.set(handle, []);
      map.get(handle)!.push(signal);
    }
    for (const [, sigs] of map) {
      sigs.sort((a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime());
    }
    return map;
  }, [recentSignals]);

  const signalsByTheme = useMemo(() => {
    const map = new Map<string, Signal[]>();
    for (const signal of recentSignals) {
      if (!signal.theme) continue;
      const theme = signal.theme.toLowerCase();
      if (!map.has(theme)) map.set(theme, []);
      map.get(theme)!.push(signal);
    }
    for (const [, sigs] of map) {
      sigs.sort((a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime());
    }
    return map;
  }, [recentSignals]);

  // Enrich voices with their recent signals using multi-strategy matching
  const enrichedVoices = useMemo((): EnrichedVoice[] => {
    return voices.map((voice) => {
      // Strategy 1: exact handle match
      const handle = voice.handle.toLowerCase();
      const byHandle = signalsByHandle.get(handle) ?? [];

      // Strategy 2: display name containment (case-insensitive)
      const displayNameLower = (voice.display_name ?? "").toLowerCase();
      const byDisplayName =
        displayNameLower.length > 2
          ? recentSignals.filter(
              (s) =>
                s.author_display_name?.toLowerCase().includes(displayNameLower) &&
                !byHandle.includes(s),
            )
          : [];

      // Strategy 3: theme-based match — signals in this voice's sector areas
      // Map sector_tags through SECTOR_TAG_TO_THEME so that tags like "vc"
      // or "investor" resolve to actual signal themes ("fintech", "ai", etc.)
      const byTheme: Signal[] = [];
      if (byHandle.length === 0 && byDisplayName.length === 0) {
        const tags = (voice.sector_tags ?? []).map((t) => t.toLowerCase());
        const resolvedThemes = new Set<string>();
        for (const tag of tags) {
          const mapped = SECTOR_TAG_TO_THEME[tag];
          if (mapped) resolvedThemes.add(mapped);
          // Also try the raw tag as a theme key (backwards compat)
          resolvedThemes.add(tag);
        }
        for (const theme of resolvedThemes) {
          const themeSignals = signalsByTheme.get(theme) ?? [];
          for (const s of themeSignals) {
            if (!byTheme.includes(s)) byTheme.push(s);
          }
        }
        byTheme.sort(
          (a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime(),
        );
      }

      const matched =
        byHandle.length > 0 ? byHandle : byDisplayName.length > 0 ? byDisplayName : byTheme;

      const recent_signals: RecentSignal[] = matched.slice(0, 5).map((s) => ({
        text: s.text,
        url: s.post_url,
        platform: s.platform,
        published_at: s.published_at,
        metrics: s.metrics as Record<string, number>,
      }));
      return {
        ...voice,
        recent_signals,
        recent_signal_count: recent_signals.length,
      };
    });
  }, [voices, signalsByHandle, signalsByTheme, recentSignals]);

  // Apply client-side search + platform filter, then reorder by persona priority
  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    const result = enrichedVoices.filter((v) => {
      if (activePlatform !== "all" && v.platform !== activePlatform) return false;
      if (q) {
        const name = (v.display_name ?? "").toLowerCase();
        const handle = v.handle.toLowerCase();
        const bio = (v.bio ?? "").toLowerCase();
        if (!name.includes(q) && !handle.includes(q) && !bio.includes(q)) return false;
      }
      return true;
    });

    // Persona reordering: float preferred account types to the top.
    // Stable sort — voices with equal weight keep their original order.
    if (persona !== "all") {
      result.sort(
        (a, b) =>
          personaSortWeight(a.account_type, persona) -
          personaSortWeight(b.account_type, persona),
      );
    }

    return result;
  }, [enrichedVoices, activePlatform, search, persona]);

  const totalPages = Math.ceil(filtered.length / VOICES_PER_PAGE);
  const safePage = Math.min(page, Math.max(1, totalPages));
  const paginatedVoices = filtered.slice(
    (safePage - 1) * VOICES_PER_PAGE,
    safePage * VOICES_PER_PAGE,
  );

  const isEmpty = voices.length === 0;

  return (
    <div id="panel-voices" role="tabpanel" aria-label="Top Voices" className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="mb-1 font-display text-[22px] text-sinal-white">Top Voices</h2>
          <p className="text-[13px] text-ash">
            Contas monitoradas, ordenadas por autoridade e sinais recentes.
          </p>
        </div>
        <span className="font-mono text-[12px] text-[#4A4A56]">
          {total.toLocaleString("pt-BR")} vozes
        </span>
      </div>

      {/* Filters */}
      <div className="space-y-3">
        {/* Search box */}
        <div className="relative max-w-sm">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#4A4A56]"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.2" />
            <path
              d="M10.5 10.5L13.5 13.5"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeLinecap="round"
            />
          </svg>
          <input
            type="search"
            placeholder="Buscar por nome ou handle..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite py-2 pl-9 pr-4 font-mono text-[12px] text-sinal-white placeholder-[#4A4A56] outline-none transition-colors focus:border-[rgba(255,255,255,0.15)]"
            aria-label="Buscar vozes"
          />
        </div>

        {/* Type filter + platform filter */}
        <div className="flex flex-wrap gap-4">
          <TypeFilter activeType={activeType} />
          <div className="h-auto w-px bg-[rgba(255,255,255,0.06)]" aria-hidden="true" />
          <PlatformFilter activePlatform={activePlatform} onChange={handlePlatformChange} />
        </div>
      </div>

      {/* Results count when filtering */}
      {(search || activePlatform !== "all") && !isEmpty && (
        <p className="font-mono text-[12px] text-[#4A4A56]">
          {filtered.length} resultado{filtered.length !== 1 ? "s" : ""} encontrado
          {filtered.length !== 1 ? "s" : ""}
        </p>
      )}

      {/* Grid or empty states */}
      {isEmpty ? (
        <div className="py-20 text-center">
          <div
            className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(255,255,255,0.04)]"
            aria-hidden="true"
          >
            <svg className="h-6 w-6 text-[#4A4A56]" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.5" />
              <path
                d="M4 20c0-4 3.6-7 8-7s8 3 8 7"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <p className="mb-1 text-[15px] text-ash">Nenhuma voz monitorada ainda.</p>
          <p className="text-[13px] text-[#4A4A56]">
            Os agentes estao coletando dados de 2.000+ investidores e fundadores.
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center">
          <p className="mb-1 text-[15px] text-ash">Nenhuma voz encontrada para esta busca.</p>
          <p className="text-[13px] text-[#4A4A56]">
            Tente outro termo ou remova os filtros ativos.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {paginatedVoices.map((voice) => (
              <VoiceCard key={voice.id} voice={voice} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] pt-6">
              <span className="font-mono text-[11px] text-[#4A4A56]">
                Pagina {safePage} de {totalPages} &mdash; {filtered.length} vozes
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={safePage <= 1}
                  className="rounded-lg border border-[rgba(255,255,255,0.06)] px-4 py-2 font-mono text-[12px] text-ash transition-all hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white disabled:cursor-not-allowed disabled:opacity-30"
                >
                  &larr; Anterior
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={safePage >= totalPages}
                  className="rounded-lg border border-[rgba(255,255,255,0.06)] px-4 py-2 font-mono text-[12px] text-ash transition-all hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white disabled:cursor-not-allowed disabled:opacity-30"
                >
                  Proxima &rarr;
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { Voice } from "@/lib/signal";
import { PLATFORM_COLORS, PLATFORM_LABELS, VOICE_TYPE_LABELS } from "@/lib/signal";

interface VoicesPanelProps {
  voices: Voice[];
  total: number;
  activeType: string;
}

const TYPE_OPTIONS = [
  { key: "all", label: "Todos" },
  { key: "founder", label: VOICE_TYPE_LABELS.founder },
  { key: "vc", label: VOICE_TYPE_LABELS.vc },
  { key: "executive", label: VOICE_TYPE_LABELS.executive },
  { key: "thought_leader", label: VOICE_TYPE_LABELS.thought_leader },
  { key: "company", label: VOICE_TYPE_LABELS.company },
];

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

function VoiceCard({ voice }: { voice: Voice }) {
  const platformColor = PLATFORM_COLORS[voice.platform] ?? "#4A4A56";
  const platformLabel = PLATFORM_LABELS[voice.platform] ?? voice.platform;
  const initial = (voice.display_name || voice.handle).charAt(0).toUpperCase();
  const authorityPct = Math.round(voice.authority_score * 100);

  const lastActive = voice.last_active
    ? new Date(voice.last_active).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "short",
      })
    : null;

  return (
    <article className="flex flex-col rounded-xl border border-sinal-slate bg-sinal-graphite p-4 transition-all duration-300 hover:border-[rgba(255,255,255,0.10)]">
      {/* Platform accent */}
      <div
        className="mb-4 h-[2px] w-full rounded-full opacity-30"
        style={{ background: `linear-gradient(90deg, ${platformColor}, transparent)` }}
        aria-hidden="true"
      />

      {/* Header */}
      <div className="mb-4 flex items-start gap-3">
        {/* Avatar */}
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-mono text-[14px] font-semibold"
          style={{ backgroundColor: `${platformColor}18`, color: platformColor }}
          aria-hidden="true"
        >
          {initial}
        </div>

        {/* Name + handle + platform */}
        <div className="min-w-0 flex-1">
          <p className="truncate font-mono text-[13px] font-semibold text-sinal-white">
            {voice.display_name || voice.handle}
          </p>
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
      {voice.bio && (
        <p className="mb-4 line-clamp-2 text-[12px] leading-[1.5] text-ash">{voice.bio}</p>
      )}

      {/* Stats */}
      <div className="mt-auto space-y-2.5 border-t border-[rgba(255,255,255,0.06)] pt-3">
        {/* Authority score bar */}
        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-[0.8px] text-[#4A4A56]">
              Autoridade
            </span>
            <span className="font-mono text-[11px] text-signal">{authorityPct}</span>
          </div>
          <div className="h-[2px] w-full overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
            <div
              className="h-full rounded-full bg-signal transition-all duration-500"
              style={{ width: `${authorityPct}%` }}
            />
          </div>
        </div>

        {/* Bottom row */}
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] text-ash">
            <span className="text-sinal-white">{voice.recent_signal_count}</span> sinais recentes
          </span>
          {lastActive && (
            <span className="font-mono text-[10px] text-[#4A4A56]">Ativo {lastActive}</span>
          )}
        </div>
      </div>
    </article>
  );
}

export default function VoicesPanel({ voices, total, activeType }: VoicesPanelProps) {
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

      {/* Type filter */}
      <TypeFilter activeType={activeType} />

      {/* Grid */}
      {voices.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {voices.map((voice) => (
            <VoiceCard key={voice.id} voice={voice} />
          ))}
        </div>
      ) : (
        <div className="py-16 text-center">
          <p className="mb-1 text-[15px] text-ash">Nenhuma voz encontrada</p>
          <p className="text-[13px] text-[#4A4A56]">
            Tente selecionar outra categoria ou aguarde a proxima coleta.
          </p>
        </div>
      )}
    </div>
  );
}

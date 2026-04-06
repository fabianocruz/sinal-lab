import Link from "next/link";
import type { WeeklyPulse } from "@/lib/signal";
import { PLATFORM_COLORS, PLATFORM_LABELS } from "@/lib/signal";

interface MemoPanelProps {
  pulse: WeeklyPulse | null;
}

function SectionHeader({ label, count }: { label: string; count?: number }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <h3 className="font-mono text-[11px] uppercase tracking-[1.5px] text-ash">{label}</h3>
      {count != null && (
        <span className="rounded bg-[rgba(255,255,255,0.06)] px-2 py-[2px] font-mono text-[10px] text-[#4A4A56]">
          {count}
        </span>
      )}
    </div>
  );
}

function EmptyPulse() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-4 h-12 w-12 rounded-full border border-sinal-slate bg-sinal-graphite flex items-center justify-center">
        <span className="font-mono text-[20px] text-[#4A4A56]">◉</span>
      </div>
      <p className="mb-1 text-[15px] text-ash">Nenhum memo disponivel</p>
      <p className="text-[13px] text-[#4A4A56]">
        O memo semanal e gerado pelo agente RADAR toda terça-feira.
      </p>
    </div>
  );
}

export default function MemoPanel({ pulse }: MemoPanelProps) {
  if (!pulse) {
    return (
      <div id="panel-memo" role="tabpanel" aria-label="Memo Semanal">
        <EmptyPulse />
      </div>
    );
  }

  const acceleratingThemes = pulse.accelerating_themes ?? [];
  const emergingSignals = pulse.emerging_signals ?? [];
  const topPosts = pulse.top_posts ?? [];
  const topVoices = pulse.top_voices ?? [];
  const startupsToWatch = pulse.startups_to_watch ?? [];
  const sectorImplications = pulse.sector_implications ?? [];

  const shareText = `Sinal Semanal — Semana ${pulse.week_number}/${pulse.year}\n\nTemas acelerando: ${acceleratingThemes
    .slice(0, 3)
    .map((t) => t.name)
    .join(", ")}\n\nsinal.tech/signals`;

  const shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`;

  return (
    <div id="panel-memo" role="tabpanel" aria-label="Memo Semanal" className="space-y-6">
      {/* Header card */}
      <div className="rounded-xl border border-[rgba(232,255,89,0.15)] bg-[rgba(232,255,89,0.04)] px-6 py-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="h-2 w-2 animate-pulse rounded-full bg-signal" aria-hidden="true" />
            <span className="font-mono text-[11px] uppercase tracking-[2px] text-signal">
              Memo Semanal
            </span>
          </div>
          <span className="font-mono text-[11px] text-ash">
            Semana {pulse.week_number} / {pulse.year}
          </span>
        </div>
        <p className="text-[14px] leading-[1.5] text-silver">
          Resumo curado dos sinais mais relevantes da semana em tecnologia, financas e startups
          LATAM, gerado pelo agente{" "}
          <span className="font-mono text-[11px] text-agent-radar">RADAR</span>.
        </p>
      </div>

      {/* Two-column layout for top sections */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Accelerating themes */}
        <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
          <SectionHeader label="5 Tendencias" count={acceleratingThemes.length} />
          {acceleratingThemes.length > 0 ? (
            <ol className="space-y-3">
              {acceleratingThemes.slice(0, 5).map((theme, i) => (
                <li key={theme.name} className="flex items-start gap-3">
                  <span className="mt-px shrink-0 font-mono text-[11px] text-[#4A4A56]">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-[13px] text-sinal-white">{theme.name}</p>
                    {theme.delta > 0 && (
                      <p className="font-mono text-[11px] text-signal">
                        +{Math.round(theme.delta * 100)}% esta semana
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-[13px] text-ash">Nenhum dado disponivel.</p>
          )}
        </div>

        {/* Emerging signals */}
        <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
          <SectionHeader label="5 Sinais" count={emergingSignals.length} />
          {emergingSignals.length > 0 ? (
            <ol className="space-y-3">
              {emergingSignals.slice(0, 5).map((signal, i) => (
                <li key={signal.name} className="flex items-start gap-3">
                  <span className="mt-px shrink-0 font-mono text-[11px] text-[#4A4A56]">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-[13px] text-sinal-white">{signal.name}</p>
                    {signal.platforms.length > 0 && (
                      <div className="mt-0.5 flex flex-wrap gap-1">
                        {signal.platforms.map((p) => (
                          <span
                            key={p}
                            className="rounded px-1 py-[1px] font-mono text-[9px] uppercase"
                            style={{
                              color: PLATFORM_COLORS[p] ?? "#8A8A96",
                              backgroundColor: `${PLATFORM_COLORS[p] ?? "#8A8A96"}14`,
                            }}
                          >
                            {PLATFORM_LABELS[p] ?? p}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-[13px] text-ash">Nenhum dado disponivel.</p>
          )}
        </div>
      </div>

      {/* Top posts */}
      {topPosts.length > 0 && (
        <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
          <SectionHeader label="Top 10 Posts" count={Math.min(topPosts.length, 10)} />
          <div className="space-y-3">
            {topPosts.slice(0, 10).map((post, i) => (
              <div
                key={i}
                className="rounded-lg border border-[rgba(255,255,255,0.04)] bg-[rgba(255,255,255,0.02)] px-4 py-3"
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="font-mono text-[10px] text-[#4A4A56]">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="font-mono text-[12px] text-silver">{post.author}</span>
                </div>
                <p className="mb-2 text-[13px] leading-[1.5] text-ash line-clamp-2">{post.text}</p>
                <Link
                  href={post.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[11px] text-ash transition-colors hover:text-sinal-white"
                >
                  Ver post &rarr;
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top voices + startups grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Top voices */}
        {topVoices.length > 0 && (
          <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
            <SectionHeader label="Top 10 Voices" count={Math.min(topVoices.length, 10)} />
            <ol className="space-y-2.5">
              {topVoices.slice(0, 10).map((voice, i) => (
                <li key={voice.handle} className="flex items-center gap-3">
                  <span className="w-5 shrink-0 text-right font-mono text-[11px] text-[#4A4A56]">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-mono text-[12px] text-sinal-white">
                      {voice.name || voice.handle}
                    </p>
                    <p className="font-mono text-[10px] text-ash">@{voice.handle}</p>
                  </div>
                  <span className="shrink-0 font-mono text-[11px] text-signal">
                    {voice.signal_count}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Startups to watch + implications */}
        <div className="space-y-4">
          {startupsToWatch.length > 0 && (
            <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
              <SectionHeader label="3 Startups para Acompanhar" count={startupsToWatch.length} />
              <ol className="space-y-3">
                {startupsToWatch.slice(0, 3).map((startup, i) => (
                  <li key={startup.slug || startup.name} className="flex items-start gap-3">
                    <span className="mt-px shrink-0 font-mono text-[11px] text-[#4A4A56]">
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      {startup.slug ? (
                        <Link
                          href={`/startup/${startup.slug}`}
                          className="font-mono text-[13px] font-semibold text-sinal-white hover:text-signal transition-colors"
                        >
                          {startup.name}
                        </Link>
                      ) : (
                        <p className="font-mono text-[13px] font-semibold text-sinal-white">
                          {startup.name}
                        </p>
                      )}
                      {startup.reason && (
                        <p className="mt-0.5 text-[12px] leading-[1.5] text-ash">
                          {startup.reason}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {sectorImplications.length > 0 && (
            <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
              <SectionHeader label="3 Implicacoes" count={sectorImplications.length} />
              <ol className="space-y-3">
                {sectorImplications.slice(0, 3).map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="mt-px shrink-0 font-mono text-[11px] text-[#4A4A56]">
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-[12px] font-semibold text-signal">
                        {item.sector}
                      </p>
                      <p className="mt-0.5 text-[12px] leading-[1.5] text-ash">
                        {item.implication}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      </div>

      {/* Share CTA */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-sinal-slate bg-sinal-graphite px-6 py-5">
        <div>
          <p className="mb-0.5 font-mono text-[13px] text-silver">
            Compartilhe o memo desta semana
          </p>
          <p className="font-mono text-[11px] text-[#4A4A56]">
            Semana {pulse.week_number}/{pulse.year}
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            href={shareUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-[rgba(255,255,255,0.08)] px-4 py-2 font-mono text-[12px] text-ash transition-all hover:border-[rgba(255,255,255,0.15)] hover:text-sinal-white"
          >
            Compartilhar no X &rarr;
          </Link>
          <Link
            href={`/signals?tab=memo`}
            className="rounded-lg border border-signal bg-[rgba(232,255,89,0.08)] px-4 py-2 font-mono text-[12px] text-signal transition-all hover:bg-[rgba(232,255,89,0.14)]"
          >
            Ver permalink
          </Link>
        </div>
      </div>
    </div>
  );
}

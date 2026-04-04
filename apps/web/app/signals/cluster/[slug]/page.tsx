import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import SignalCard from "@/components/signals/SignalCard";
import DimensionRadar from "@/components/signals/DimensionRadar";
import { fetchSignalClusterBySlug, fetchSignals } from "@/lib/api";
import { STAGE_COLORS, STAGE_LABELS, PLATFORM_COLORS } from "@/lib/signal";

export const revalidate = 300;

interface ClusterDetailPageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: ClusterDetailPageProps): Promise<Metadata> {
  const cluster = await fetchSignalClusterBySlug(params.slug);
  if (!cluster) return { title: "Cluster | Sinal" };
  return {
    title: `${cluster.name} | Sinais | Sinal`,
    description: cluster.description || `Cluster de sinais sobre ${cluster.theme}.`,
    openGraph: {
      title: `${cluster.name} | Sinais | Sinal`,
      description: cluster.description || `Cluster de sinais sobre ${cluster.theme}.`,
      type: "website",
    },
  };
}

export default async function ClusterDetailPage({ params }: ClusterDetailPageProps) {
  const [cluster, signalsData] = await Promise.all([
    fetchSignalClusterBySlug(params.slug),
    fetchSignals({ theme: params.slug, limit: 12, offset: 0 }),
  ]);

  if (!cluster) notFound();

  const stageColor = STAGE_COLORS[cluster.narrative_stage] ?? "#8A8A96";
  const stageLabel = STAGE_LABELS[cluster.narrative_stage] ?? cluster.narrative_stage;
  const scorePercent = Math.round(cluster.composite_score * 100);

  const dimensionEntries = Object.entries(cluster.dimensions ?? {}).sort(([, a], [, b]) => b - a);

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-[1120px] px-[clamp(20px,4vw,48px)] py-10">
          {/* Back link */}
          <Link
            href="/signals"
            className="mb-8 inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
          >
            &larr; Todos os sinais
          </Link>

          {/* Header */}
          <div className="mb-10">
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <span className="font-mono text-[11px] uppercase tracking-[1px] text-ash">
                {cluster.theme}
                {cluster.sub_theme ? ` / ${cluster.sub_theme}` : ""}
              </span>
              <span
                className="rounded px-2 py-[3px] font-mono text-[9px] font-semibold uppercase tracking-[1px]"
                style={{ color: stageColor, backgroundColor: `${stageColor}14` }}
              >
                {stageLabel}
              </span>
              <span className="font-mono text-[11px] text-ash">
                Semana {cluster.week_number}/{cluster.year}
              </span>
            </div>

            <h1 className="mb-4 font-display text-[clamp(26px,4vw,40px)] leading-[1.2] text-sinal-white">
              {cluster.name}
            </h1>

            {cluster.description && (
              <p className="max-w-[680px] text-[16px] leading-[1.6] text-ash">
                {cluster.description}
              </p>
            )}
          </div>

          {/* Two-column layout: score breakdown + top voices */}
          <div className="mb-10 grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Composite score + dimensions */}
            <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-6">
              <h2 className="mb-1 font-mono text-[11px] uppercase tracking-[1.5px] text-ash">
                Score Composto
              </h2>
              <div
                className="mb-4 font-display text-[48px] leading-none"
                style={{ color: stageColor }}
              >
                {scorePercent}
              </div>

              {/* Progress bar */}
              <div className="mb-6 h-[4px] w-full overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${scorePercent}%`, backgroundColor: stageColor }}
                />
              </div>

              {/* Dimension radar chart */}
              {dimensionEntries.length > 0 && (
                <div>
                  <p className="mb-2 font-mono text-[10px] uppercase tracking-[1px] text-[#4A4A56]">
                    Dimensoes
                  </p>
                  <DimensionRadar dimensions={cluster.dimensions} accentColor={stageColor} />
                </div>
              )}
            </div>

            {/* Top voices */}
            {cluster.top_voices.length > 0 && (
              <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-6">
                <h2 className="mb-4 font-mono text-[11px] uppercase tracking-[1.5px] text-ash">
                  Vozes Influentes
                </h2>
                <div className="space-y-4">
                  {cluster.top_voices.slice(0, 5).map((voice, index) => (
                    <div key={voice.handle} className="flex items-center gap-3">
                      {/* Rank */}
                      <span className="w-4 shrink-0 text-right font-mono text-[11px] text-[#4A4A56]">
                        {index + 1}
                      </span>

                      {/* Avatar initial */}
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[rgba(255,255,255,0.06)] font-mono text-[12px] text-silver">
                        {(voice.name || voice.handle).charAt(0).toUpperCase()}
                      </div>

                      {/* Name + handle */}
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-mono text-[13px] font-semibold text-sinal-white">
                          {voice.name || voice.handle}
                        </p>
                        <p className="font-mono text-[11px] text-ash">@{voice.handle}</p>
                      </div>

                      {/* Authority score */}
                      <span className="shrink-0 font-mono text-[12px] text-signal">
                        {Math.round(voice.authority * 100)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Top posts */}
          {cluster.top_posts.length > 0 && (
            <div className="mb-10">
              <h2 className="mb-4 font-display text-[20px] text-sinal-white">Posts em Destaque</h2>
              <div className="space-y-3">
                {cluster.top_posts.slice(0, 4).map((post, index) => {
                  const platformColor = PLATFORM_COLORS[post.platform] ?? "#4A4A56";
                  return (
                    <div
                      key={index}
                      className="rounded-xl border border-sinal-slate bg-sinal-graphite px-5 py-4"
                    >
                      <div className="mb-2 flex items-center gap-2">
                        <span
                          className="h-[6px] w-[6px] rounded-full"
                          style={{ backgroundColor: platformColor }}
                          aria-hidden="true"
                        />
                        <span className="font-mono text-[11px] text-ash">{post.author}</span>
                        <span className="font-mono text-[10px] uppercase tracking-[0.5px] text-[#4A4A56]">
                          {post.platform}
                        </span>
                      </div>
                      <p className="mb-3 text-[14px] leading-[1.55] text-silver">{post.text}</p>
                      <Link
                        href={post.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-[11px] text-ash transition-colors hover:text-sinal-white"
                      >
                        Ver post &rarr;
                      </Link>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Related signals from feed */}
          {signalsData.items.length > 0 && (
            <div className="mb-10">
              <h2 className="mb-4 font-display text-[20px] text-sinal-white">
                Sinais Relacionados
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {signalsData.items.map((signal) => (
                  <SignalCard key={signal.id} signal={signal} />
                ))}
              </div>
            </div>
          )}

          {/* Stats summary bar */}
          <div className="rounded-xl border border-sinal-slate bg-sinal-graphite px-6 py-5">
            <div className="flex flex-wrap items-center gap-8">
              <div className="text-center">
                <div className="font-display text-[24px] leading-none text-sinal-white">
                  {cluster.signal_count.toLocaleString("pt-BR")}
                </div>
                <div className="mt-1 font-mono text-[9px] uppercase tracking-[1px] text-[#4A4A56]">
                  Sinais
                </div>
              </div>
              <div className="w-px bg-sinal-slate" />
              <div className="text-center">
                <div
                  className="font-display text-[24px] leading-none"
                  style={{ color: stageColor }}
                >
                  {scorePercent}
                </div>
                <div className="mt-1 font-mono text-[9px] uppercase tracking-[1px] text-[#4A4A56]">
                  Score
                </div>
              </div>
              <div className="w-px bg-sinal-slate" />
              <div className="text-center">
                <div className="font-display text-[24px] leading-none text-sinal-white">
                  {cluster.top_voices.length}
                </div>
                <div className="mt-1 font-mono text-[9px] uppercase tracking-[1px] text-[#4A4A56]">
                  Vozes
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

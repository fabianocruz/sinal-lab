import { Suspense } from "react";
import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import FeedItem from "@/components/feed/FeedItem";
import FeedFilterBar from "@/components/feed/FeedFilterBar";
import TrendingSidebar from "@/components/feed/TrendingSidebar";
import Pagination from "@/components/newsletter/Pagination";
import { fetchSignals, fetchSignalClusters, fetchSignalStats } from "@/lib/api";

// ---------------------------------------------------------------------------
// ISR — refresh every 60 seconds (signals update frequently)
// ---------------------------------------------------------------------------

export const revalidate = 60;

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

export const metadata: Metadata = {
  title: "Feed | Sinal",
  description:
    "Sinais em tempo real sobre AI, Fintech e Banking de multiplas fontes: Twitter/X, Reddit, Bluesky, YouTube, newsletters e mais.",
  openGraph: {
    title: "Feed | Sinal",
    description: "Sinais em tempo real sobre AI, Fintech e Banking de multiplas fontes.",
    type: "website",
  },
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 30;

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function FeedPage({
  searchParams,
}: {
  searchParams: { platform?: string; theme?: string; page?: string };
}) {
  const page = Math.max(1, parseInt(searchParams.page ?? "1", 10));
  const offset = (page - 1) * PAGE_SIZE;

  const platform = searchParams.platform ?? "";
  const theme = searchParams.theme ?? "";

  // Fetch signals, clusters, and stats in parallel
  const [signalsData, clustersData, stats] = await Promise.all([
    fetchSignals({
      platform: platform || undefined,
      theme: theme || undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    fetchSignalClusters({ limit: 20 }),
    fetchSignalStats(),
  ]);

  const signals = signalsData.items;
  const totalPages = Math.max(1, Math.ceil(signalsData.total / PAGE_SIZE));

  // Active filter label for the header
  const filterSummary = [
    platform ? platform.charAt(0).toUpperCase() + platform.slice(1) : null,
    theme || null,
  ]
    .filter(Boolean)
    .join(" + ");

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        {/* ----------------------------------------------------------------
            Vibrant hero header — RADAR mint on dark
        ----------------------------------------------------------------- */}
        <div className="bg-[#59FFB4]">
          <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] py-12">
            <div className="mb-2 flex items-center gap-2">
              <span
                className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[rgba(0,0,0,0.4)]"
                aria-hidden="true"
              />
              <span className="font-mono text-[10px] uppercase tracking-[2px] text-[rgba(0,0,0,0.5)]">
                Tempo real
              </span>
            </div>
            <h1 className="mb-2 font-display text-[clamp(32px,5vw,48px)] text-sinal-black">Feed</h1>
            <p className="max-w-[500px] text-[16px] leading-[1.6] text-[rgba(0,0,0,0.7)]">
              Sinais de AI, Fintech e Banking de multiplas fontes, atualizados em tempo real.
              {stats.total_signals > 0 && (
                <span className="ml-1 font-semibold text-[rgba(0,0,0,0.5)]">
                  {stats.total_signals.toLocaleString("pt-BR")} sinais indexados.
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)]">
          {/* ----------------------------------------------------------------
              Filter bar — dark section with colored top border
          ----------------------------------------------------------------- */}
          <div className="mb-8 border-t-[3px] border-[#59FFB4] pt-6">
            <Suspense fallback={<FilterBarFallback />}>
              <FeedFilterBar />
            </Suspense>
          </div>

          {/* ----------------------------------------------------------------
              Active filter banner
          ----------------------------------------------------------------- */}
          {filterSummary && (
            <div className="mb-6 flex items-center gap-2.5 rounded-lg border border-[rgba(232,255,89,0.15)] bg-[rgba(232,255,89,0.04)] px-4 py-2.5">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-signal" aria-hidden="true" />
              <p className="text-[12px] text-silver">
                Filtrando por: <span className="font-semibold text-signal">{filterSummary}</span>
              </p>
            </div>
          )}

          {/* ----------------------------------------------------------------
              Main layout: feed + sidebar
          ----------------------------------------------------------------- */}
          <div className="flex gap-10">
            {/* Feed column */}
            <div className="min-w-0 flex-1">
              {signals.length === 0 ? (
                <EmptyState platform={platform} theme={theme} />
              ) : (
                <>
                  <ul aria-label="Feed de sinais">
                    {signals.map((signal) => (
                      <li key={signal.id}>
                        <FeedItem signal={signal} />
                      </li>
                    ))}
                  </ul>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="py-8">
                      <Pagination currentPage={page} totalPages={totalPages} basePath="/feed" />
                    </div>
                  )}
                </>
              )}

              {/* Signal count / page info */}
              {signals.length > 0 && (
                <p className="pb-8 pt-4 font-mono text-[11px] text-[#4A4A56]">
                  Mostrando {offset + 1}–{Math.min(offset + signals.length, signalsData.total)} de{" "}
                  {signalsData.total.toLocaleString("pt-BR")} sinais
                </p>
              )}
            </div>

            {/* Sidebar — hidden on mobile */}
            <div className="hidden w-[280px] shrink-0 lg:block">
              <div className="sticky top-[88px]">
                <TrendingSidebar clusters={clustersData.items} />

                {/* Methodology note */}
                <div className="mt-6 rounded-xl border border-sinal-slate bg-sinal-graphite px-4 py-4">
                  <p className="mb-1 font-mono text-[10px] uppercase tracking-[2px] text-[#4A4A56]">
                    Metodologia
                  </p>
                  <p className="text-[12px] leading-[1.6] text-ash">
                    Sinais coletados e classificados pelo agente{" "}
                    <span className="font-mono text-[11px] text-agent-radar">RADAR</span>.
                    Atualizado a cada hora.
                  </p>
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

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState({ platform, theme }: { platform: string; theme: string }) {
  const hasFilter = platform || theme;
  return (
    <div className="py-20 text-center">
      <p className="mb-2 font-mono text-[11px] uppercase tracking-[2px] text-ash">
        Nenhum sinal encontrado
      </p>
      <p className="text-[15px] text-silver">
        {hasFilter
          ? "Tente remover os filtros ou ampliar o intervalo de busca."
          : "Nenhum sinal disponivel no momento. Volte em breve."}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filter bar fallback (static placeholder while Suspense resolves)
// ---------------------------------------------------------------------------

function FilterBarFallback() {
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-8 w-20 animate-pulse rounded-lg bg-sinal-graphite" />
        ))}
      </div>
      <div className="flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-8 w-24 animate-pulse rounded-lg bg-sinal-graphite" />
        ))}
      </div>
    </div>
  );
}

import type { Metadata } from "next";
import { Suspense } from "react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Pagination from "@/components/newsletter/Pagination";
import StatsBar from "@/components/signals/StatsBar";
import ClusterCard from "@/components/signals/ClusterCard";
import SignalCard from "@/components/signals/SignalCard";
import PlatformFilter from "@/components/signals/PlatformFilter";
import { fetchSignalStats, fetchSignalClusters, fetchSignals, fetchLatestPulse } from "@/lib/api";

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Social Signal Intelligence | Sinal",
  description:
    "Sinais emergentes em AI, Fintech e Banking detectados por inteligencia artificial. Clusters de tendencias, vozes influentes e posts relevantes.",
  openGraph: {
    title: "Social Signal Intelligence | Sinal",
    description:
      "Sinais emergentes em AI, Fintech e Banking detectados por inteligencia artificial.",
    type: "website",
  },
};

const CLUSTERS_PER_PAGE = 9;
const SIGNALS_PER_PAGE = 12;

export default async function SignalsPage({
  searchParams,
}: {
  searchParams: {
    theme?: string;
    platform?: string;
    page?: string;
    signals_page?: string;
  };
}) {
  const clustersPage = parseInt(searchParams.page ?? "1", 10);
  const signalsPage = parseInt(searchParams.signals_page ?? "1", 10);

  const [stats, clustersData, signalsData, pulse] = await Promise.all([
    fetchSignalStats(),
    fetchSignalClusters({
      theme: searchParams.theme,
      limit: CLUSTERS_PER_PAGE,
      offset: (clustersPage - 1) * CLUSTERS_PER_PAGE,
    }),
    fetchSignals({
      platform: searchParams.platform,
      theme: searchParams.theme,
      limit: SIGNALS_PER_PAGE,
      offset: (signalsPage - 1) * SIGNALS_PER_PAGE,
    }),
    fetchLatestPulse(),
  ]);

  const totalClusterPages = Math.max(1, Math.ceil(clustersData.total / CLUSTERS_PER_PAGE));
  const totalSignalPages = Math.max(1, Math.ceil(signalsData.total / SIGNALS_PER_PAGE));

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        {/* Hero section */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pt-12">
          <div className="mb-2 flex flex-wrap items-end justify-between gap-6">
            <div>
              <span className="mb-2.5 block font-mono text-[10px] uppercase tracking-[2px] text-signal">
                Intelligence
              </span>
              <h1 className="mb-2 font-display text-[clamp(28px,4vw,36px)] leading-[1.2] text-sinal-white">
                Social Signal Intelligence
              </h1>
              <p className="max-w-[520px] text-[15px] leading-[1.5] text-ash">
                Sinais emergentes detectados por IA em conversas publicas sobre AI, Fintech e
                Banking. Atualizado semanalmente pelo agente{" "}
                <span className="font-mono text-[12px] text-agent-radar">RADAR</span>.
              </p>
            </div>

            {/* Stats box */}
            <StatsBar stats={stats} />
          </div>
        </div>

        {/* Weekly pulse summary */}
        {pulse && pulse.accelerating_themes.length > 0 && (
          <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pt-8">
            <div className="rounded-xl border border-[rgba(232,255,89,0.12)] bg-[rgba(232,255,89,0.04)] px-6 py-5">
              <div className="mb-3 flex items-center gap-2">
                <div className="h-2 w-2 animate-pulse rounded-full bg-signal" />
                <span className="font-mono text-[10px] uppercase tracking-[2px] text-signal">
                  Pulse da Semana {pulse.week_number}/{pulse.year}
                </span>
              </div>
              <div className="flex flex-wrap gap-3">
                {pulse.accelerating_themes.slice(0, 5).map((theme) => (
                  <div
                    key={theme.name}
                    className="flex items-center gap-2 rounded-lg border border-[rgba(232,255,89,0.10)] bg-[rgba(232,255,89,0.06)] px-3 py-1.5"
                  >
                    <span className="text-[13px] text-silver">{theme.name}</span>
                    {theme.delta > 0 && (
                      <span className="font-mono text-[11px] text-signal">
                        +{Math.round(theme.delta * 100)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Clusters section */}
        <div className="mx-auto max-w-[1280px] border-b border-sinal-slate px-[clamp(20px,4vw,32px)] pb-10 pt-10">
          <div className="mb-6">
            <h2 className="mb-1 font-display text-[22px] text-sinal-white">Clusters de Sinais</h2>
            <p className="text-[13px] text-ash">
              Grupos de sinais relacionados, ordenados por relevancia composta.
            </p>
          </div>

          {clustersData.items.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {clustersData.items.map((cluster) => (
                <ClusterCard key={cluster.id} cluster={cluster} />
              ))}
            </div>
          ) : (
            <div className="py-16 text-center">
              <p className="mb-1 text-[15px] text-ash">Nenhum cluster encontrado</p>
              <p className="text-[13px] text-[#4A4A56]">
                Os clusters sao gerados pelo agente RADAR semanalmente.
              </p>
            </div>
          )}

          {clustersData.items.length > 0 && (
            <Pagination
              currentPage={clustersPage}
              totalPages={totalClusterPages}
              basePath="/signals"
            />
          )}
        </div>

        {/* Signals feed section */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pb-12 pt-10">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="mb-1 font-display text-[22px] text-sinal-white">Feed de Sinais</h2>
              <p className="text-[13px] text-ash">Posts individuais capturados por plataforma.</p>
            </div>
            <span className="font-mono text-[12px] tracking-[0.5px] text-[#4A4A56]">
              {signalsData.total.toLocaleString("pt-BR")} sinais
              {searchParams.platform ? ` no ${searchParams.platform}` : ""}
            </span>
          </div>

          {/* Platform filter — Client Component */}
          <div className="mb-6">
            <Suspense fallback={null}>
              <PlatformFilter />
            </Suspense>
          </div>

          {signalsData.items.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {signalsData.items.map((signal) => (
                <SignalCard key={signal.id} signal={signal} />
              ))}
            </div>
          ) : (
            <div className="py-16 text-center">
              <p className="mb-1 text-[15px] text-ash">Nenhum sinal encontrado</p>
              <p className="text-[13px] text-[#4A4A56]">Tente selecionar outra plataforma.</p>
            </div>
          )}

          {signalsData.items.length > 0 && (
            <Pagination
              currentPage={signalsPage}
              totalPages={totalSignalPages}
              basePath="/signals"
            />
          )}
        </div>

        {/* Methodology badge */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pb-12">
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-sinal-slate bg-sinal-graphite px-6 py-5">
            <div className="flex items-center gap-4">
              <div className="h-2 w-2 animate-pulse rounded-full bg-agent-radar" />
              <div>
                <p className="mb-0.5 text-[13px] text-silver">
                  Sinais coletados e clusterizados pelo agente{" "}
                  <span className="font-mono text-[11px] text-agent-radar">RADAR</span>
                </p>
                <p className="font-mono text-[11px] text-[#4A4A56]">
                  Fontes: Twitter/X, Reddit, Bluesky, LinkedIn
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

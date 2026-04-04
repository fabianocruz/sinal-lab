import type { Metadata } from "next";
import { Suspense } from "react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import StatsBar from "@/components/signals/StatsBar";
import TabNav from "@/components/signals/TabNav";
import PulsePanel from "@/components/signals/PulsePanel";
import VoicesPanel from "@/components/signals/VoicesPanel";
import StartupsPanel from "@/components/signals/StartupsPanel";
import BankingPanel from "@/components/signals/BankingPanel";
import MemoPanel from "@/components/signals/MemoPanel";
import type { SignalsTab } from "@/components/signals/TabNav";
import {
  fetchSignalStats,
  fetchSignalClusters,
  fetchSignals,
  fetchLatestPulse,
  fetchVoices,
  fetchSignalEntities,
  fetchCompanies,
} from "@/lib/api";

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

const VALID_TABS: SignalsTab[] = ["pulse", "voices", "startups", "banking", "memo"];

function isValidTab(value: string | undefined): value is SignalsTab {
  return VALID_TABS.includes(value as SignalsTab);
}

export default async function SignalsPage({
  searchParams,
}: {
  searchParams: {
    tab?: string;
    type?: string; // voices panel filter
  };
}) {
  const activeTab: SignalsTab = isValidTab(searchParams.tab) ? searchParams.tab : "pulse";
  const voiceType = searchParams.type ?? "all";

  // Always fetch stats (used in header) and pulse (used in pulse + memo panels)
  const [stats, pulse] = await Promise.all([fetchSignalStats(), fetchLatestPulse()]);

  // Fetch data for the active tab only to keep page fast
  const [
    clustersData,
    voicesData,
    voicesSignalsData,
    entitiesData,
    bankingSignalsData,
    startupsSignalsData,
    companiesData,
  ] = await Promise.all([
    // Pulse and Banking tabs need clusters
    activeTab === "pulse" || activeTab === "banking"
      ? fetchSignalClusters({
          theme: activeTab === "banking" ? "AI in Banking" : undefined,
          limit: activeTab === "banking" ? 10 : 20,
        })
      : Promise.resolve({ items: [], total: 0, limit: 20, offset: 0 }),

    // Voices tab — accounts
    activeTab === "voices"
      ? fetchVoices({
          account_type: voiceType === "all" ? undefined : voiceType,
          limit: 50,
        })
      : Promise.resolve({ items: [], total: 0, limit: 50, offset: 0 }),

    // Voices tab — recent signals to join with voices
    activeTab === "voices"
      ? fetchSignals({ limit: 100 })
      : Promise.resolve({ items: [], total: 0, limit: 100, offset: 0 }),

    // Startups tab — dedicated entities endpoint
    activeTab === "startups"
      ? fetchSignalEntities({ limit: 30 })
      : Promise.resolve({ items: [], total: 0, limit: 30, offset: 0 }),

    // Banking tab — signals
    activeTab === "banking"
      ? fetchSignals({ theme: "AI in Banking", limit: 9 })
      : Promise.resolve({ items: [], total: 0, limit: 9, offset: 0 }),

    // Startups tab — signals as fallback for entity extraction
    activeTab === "startups"
      ? fetchSignals({ limit: 100 })
      : Promise.resolve({ items: [], total: 0, limit: 100, offset: 0 }),

    // Startups tab — known companies for accurate entity matching
    activeTab === "startups"
      ? fetchCompanies({ limit: 100 })
      : Promise.resolve({ items: [], total: 0, limit: 100, offset: 0 }),
  ]);

  // For pulse tab we need all clusters (not banking-filtered)
  const pulseClusters = activeTab === "pulse" ? clustersData.items : [];

  // For banking tab the clustersData IS already banking-filtered
  const bankingClusters = activeTab === "banking" ? clustersData.items : [];

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        {/* Hero section */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pt-12">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-6">
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

        {/* Tab navigation — Client Component */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)]">
          <div className="border-b border-sinal-slate">
            <Suspense fallback={<TabNavSkeleton />}>
              <TabNav activeTab={activeTab} />
            </Suspense>
          </div>
        </div>

        {/* Panel content */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pb-16 pt-8">
          {activeTab === "pulse" && (
            <PulsePanel pulse={pulse} clusters={pulseClusters} stats={stats} />
          )}

          {activeTab === "voices" && (
            <VoicesPanel
              voices={voicesData.items}
              recentSignals={voicesSignalsData.items}
              total={voicesData.total}
              activeType={voiceType}
            />
          )}

          {activeTab === "startups" && (
            <StartupsPanel
              entities={entitiesData.items}
              total={entitiesData.total}
              fallbackSignals={startupsSignalsData.items}
              knownCompanies={companiesData.items}
            />
          )}

          {activeTab === "banking" && (
            <BankingPanel
              bankingSignals={bankingSignalsData.items}
              bankingClusters={bankingClusters}
              totalSignals={bankingSignalsData.total}
            />
          )}

          {activeTab === "memo" && <MemoPanel pulse={pulse} />}
        </div>

        {/* Methodology badge */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pb-12">
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-sinal-slate bg-sinal-graphite px-6 py-5">
            <div className="flex items-center gap-4">
              <div
                className="h-2 w-2 animate-pulse rounded-full bg-agent-radar"
                aria-hidden="true"
              />
              <div>
                <p className="mb-0.5 text-[13px] text-silver">
                  Sinais coletados e clusterizados pelo agente{" "}
                  <span className="font-mono text-[11px] text-agent-radar">RADAR</span>
                </p>
                <p className="font-mono text-[11px] text-[#4A4A56]">
                  Fontes: Twitter/X, Reddit, Bluesky, LinkedIn &mdash; atualizado semanalmente
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

function TabNavSkeleton() {
  return (
    <div className="flex gap-1">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-10 w-28 animate-pulse rounded-t-lg bg-sinal-graphite" />
      ))}
    </div>
  );
}

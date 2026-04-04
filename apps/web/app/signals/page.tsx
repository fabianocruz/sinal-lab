import type { Metadata } from "next";
import { Suspense } from "react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import StatsBar from "@/components/signals/StatsBar";
import ExportButton from "@/components/signals/ExportButton";
import TabNav from "@/components/signals/TabNav";
import PulsePanel from "@/components/signals/PulsePanel";
import VoicesPanel from "@/components/signals/VoicesPanel";
import EmpresasPanel from "@/components/signals/EmpresasPanel";
import TemasPanel from "@/components/signals/TemasPanel";
import MemoPanel from "@/components/signals/MemoPanel";
import PersonaSelector from "@/components/signals/PersonaSelector";
import type { SignalsTab } from "@/components/signals/TabNav";
import type { Persona } from "@/components/signals/PersonaSelector";
import { PERSONA_LABELS, resolvePersona } from "@/components/signals/PersonaSelector";
import {
  fetchSignalStats,
  fetchSignalClusters,
  fetchSignals,
  fetchLatestPulse,
  fetchVoices,
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

const VALID_TABS: SignalsTab[] = ["pulse", "voices", "empresas", "temas", "memo"];

// Legacy tab keys from old URLs — redirect to their replacements
const TAB_ALIASES: Record<string, SignalsTab> = {
  startups: "empresas",
  banking: "temas",
};

function resolveTab(value: string | undefined): SignalsTab {
  if (!value) return "pulse";
  if (TAB_ALIASES[value]) return TAB_ALIASES[value];
  if (VALID_TABS.includes(value as SignalsTab)) return value as SignalsTab;
  return "pulse";
}

export default async function SignalsPage({
  searchParams,
}: {
  searchParams: {
    tab?: string;
    type?: string; // voices panel filter
    persona?: string; // persona selector
  };
}) {
  const activeTab: SignalsTab = resolveTab(searchParams.tab);
  const voiceType = searchParams.type ?? "all";
  const activePersona: Persona = resolvePersona(searchParams.persona);

  // Always fetch stats (used in header) and pulse (used in pulse + memo panels)
  const [stats, pulse] = await Promise.all([fetchSignalStats(), fetchLatestPulse()]);

  // Fetch data for the active tab only to keep page fast
  const [clustersData, voicesData, voicesSignalsData, temasSignalsData, companiesData] =
    await Promise.all([
      // Pulse and Temas tabs need clusters
      activeTab === "pulse" || activeTab === "temas"
        ? fetchSignalClusters({ limit: 20 })
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

      // Temas tab — all signals (TemasPanel filters client-side by theme)
      activeTab === "temas"
        ? fetchSignals({ limit: 50 })
        : Promise.resolve({ items: [], total: 0, limit: 50, offset: 0 }),

      // Empresas tab — known companies + signals for matching
      activeTab === "empresas"
        ? fetchCompanies({ limit: 200 })
        : Promise.resolve({ items: [], total: 0, limit: 200, offset: 0 }),
    ]);

  // Empresas tab also needs signals to match against
  const empresasSignalsData =
    activeTab === "empresas"
      ? await fetchSignals({ limit: 200 })
      : { items: [], total: 0, limit: 200, offset: 0 };

  const pulseClusters = activeTab === "pulse" ? clustersData.items : [];
  const temasClusters = activeTab === "temas" ? clustersData.items : [];

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

            {/* Stats box + export */}
            <div className="flex flex-wrap items-end gap-3">
              <StatsBar stats={stats} />
              <ExportButton />
            </div>
          </div>
        </div>

        {/* Persona selector + optional active banner */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pb-4">
          <Suspense fallback={null}>
            <PersonaSelector activePersona={activePersona} />
          </Suspense>
          {activePersona !== "all" && (
            <div className="mt-3 flex items-center gap-2.5 rounded-lg border border-[rgba(232,255,89,0.15)] bg-[rgba(232,255,89,0.04)] px-4 py-2.5">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-signal" aria-hidden="true" />
              <p className="text-[12px] text-silver">
                Mostrando sinais relevantes para{" "}
                <span className="font-semibold text-signal">{PERSONA_LABELS[activePersona]}</span>
              </p>
            </div>
          )}
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
              persona={activePersona}
            />
          )}

          {activeTab === "empresas" && (
            <EmpresasPanel companies={companiesData.items} signals={empresasSignalsData.items} />
          )}

          {activeTab === "temas" && (
            <TemasPanel clusters={temasClusters} signals={temasSignalsData.items} />
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

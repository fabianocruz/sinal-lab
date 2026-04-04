import Link from "next/link";
import type { Signal, SignalCluster } from "@/lib/signal";
import { STAGE_COLORS, STAGE_LABELS } from "@/lib/signal";
import SignalCard from "@/components/signals/SignalCard";
import ScoreBar from "@/components/signals/ScoreBar";

interface BankingPanelProps {
  bankingSignals: Signal[];
  bankingClusters: SignalCluster[];
  totalSignals: number;
}

// Sub-themes relevant to AI in Banking
const BANKING_SUBTOPICS = [
  { key: "credit_scoring", label: "Credit Scoring" },
  { key: "fraud_detection", label: "Fraud Detection" },
  { key: "open_banking", label: "Open Banking" },
  { key: "payments", label: "Pagamentos" },
  { key: "compliance", label: "Compliance / Regulacao" },
  { key: "conversational_banking", label: "Banking Conversacional" },
  { key: "risk", label: "Gestao de Risco" },
];

function SubtopicMaturity({ clusters }: { clusters: SignalCluster[] }) {
  if (clusters.length === 0) {
    return (
      <div className="py-8 text-center">
        <p className="text-[13px] text-ash">Nenhum sub-tema encontrado.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {clusters.map((cluster) => {
        const stageColor = STAGE_COLORS[cluster.narrative_stage] ?? "#8A8A96";
        const stageLabel = STAGE_LABELS[cluster.narrative_stage] ?? cluster.narrative_stage;

        return (
          <Link
            key={cluster.id}
            href={`/signals/cluster/${cluster.slug}`}
            className="block rounded-xl border border-sinal-slate bg-[rgba(255,255,255,0.02)] px-5 py-4 transition-all hover:border-[rgba(255,255,255,0.10)] hover:bg-[rgba(255,255,255,0.04)]"
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="truncate font-mono text-[13px] font-semibold text-sinal-white">
                  {cluster.name}
                </p>
                {cluster.sub_theme && (
                  <p className="font-mono text-[11px] text-ash">{cluster.sub_theme}</p>
                )}
              </div>
              <span
                className="mt-0.5 shrink-0 rounded px-2 py-[3px] font-mono text-[9px] uppercase tracking-[0.8px]"
                style={{ color: stageColor, backgroundColor: `${stageColor}14` }}
              >
                {stageLabel}
              </span>
            </div>

            {/* Maturity bar via ScoreBar */}
            <ScoreBar score={cluster.composite_score} color={stageColor} />

            {/* Signal count + top voices */}
            <div className="mt-2.5 flex items-center justify-between">
              <span className="font-mono text-[11px] text-ash">
                <span className="text-silver">{cluster.signal_count}</span> sinais
              </span>
              {cluster.top_voices.length > 0 && (
                <div className="flex -space-x-1.5">
                  {cluster.top_voices.slice(0, 4).map((v) => {
                    const initial = (v.name || v.handle).charAt(0).toUpperCase();
                    return (
                      <div
                        key={v.handle}
                        className="flex h-5 w-5 items-center justify-center rounded-full border border-sinal-black bg-[rgba(255,255,255,0.08)] font-mono text-[8px] text-silver"
                        title={v.name || v.handle}
                        aria-label={v.name || v.handle}
                      >
                        {initial}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function TopicGrid() {
  return (
    <div className="flex flex-wrap gap-2">
      {BANKING_SUBTOPICS.map((topic) => (
        <span
          key={topic.key}
          className="rounded-lg border border-[rgba(255,255,255,0.06)] px-3 py-1.5 font-mono text-[12px] text-ash"
        >
          {topic.label}
        </span>
      ))}
    </div>
  );
}

export default function BankingPanel({
  bankingSignals,
  bankingClusters,
  totalSignals,
}: BankingPanelProps) {
  return (
    <div id="panel-banking" role="tabpanel" aria-label="Banking Relevance" className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="mb-1 font-display text-[22px] text-sinal-white">AI in Banking</h2>
          <p className="text-[13px] text-ash">
            Sinais e tendencias filtrados para o setor bancario e financeiro.
          </p>
        </div>
        {totalSignals > 0 && (
          <span className="font-mono text-[12px] text-[#4A4A56]">
            {totalSignals.toLocaleString("pt-BR")} sinais no tema
          </span>
        )}
      </div>

      {/* Sub-themes we track */}
      <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
        <h3 className="mb-3 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
          Sub-temas Monitorados
        </h3>
        <TopicGrid />
      </div>

      {/* Clusters / maturity */}
      <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
        <h3 className="mb-1 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">
          Maturidade por Sub-tema
        </h3>
        <p className="mb-4 text-[12px] text-[#4A4A56]">
          Clusters detectados no tema AI in Banking, ordenados por score composto.
        </p>
        <SubtopicMaturity clusters={bankingClusters} />
      </div>

      {/* Recent signals feed */}
      <div>
        <h3 className="mb-4 font-display text-[18px] text-sinal-white">Sinais Recentes</h3>
        {bankingSignals.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {bankingSignals.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        ) : (
          <div className="py-16 text-center">
            <p className="mb-1 text-[15px] text-ash">Nenhum sinal encontrado</p>
            <p className="text-[13px] text-[#4A4A56]">
              Sinais de AI in Banking aparecem apos proxima coleta do agente RADAR.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

import Link from "next/link";
import type { SignalEntity } from "@/lib/signal";

interface StartupsPanelProps {
  entities: SignalEntity[];
  total: number;
}

function sentimentColor(sentiment: number): string {
  if (sentiment > 0.2) return "#59FFB4"; // positive — agent-radar green
  if (sentiment < -0.2) return "#FF8A59"; // negative — agent-funding orange
  return "#8A8A96"; // neutral — ash
}

function sentimentLabel(sentiment: number): string {
  if (sentiment > 0.2) return "Positivo";
  if (sentiment < -0.2) return "Negativo";
  return "Neutro";
}

function EntityRow({ entity, rank }: { entity: SignalEntity; rank: number }) {
  const sColor = sentimentColor(entity.sentiment);
  const sLabel = sentimentLabel(entity.sentiment);

  const inner = (
    <div className="flex items-center gap-4 rounded-xl border border-sinal-slate bg-sinal-graphite px-5 py-4 transition-all duration-200 hover:border-[rgba(255,255,255,0.10)]">
      {/* Rank */}
      <span className="w-5 shrink-0 text-right font-mono text-[12px] text-[#4A4A56]">{rank}</span>

      {/* Name + theme */}
      <div className="min-w-0 flex-1">
        <p className="truncate font-mono text-[14px] font-semibold text-sinal-white">
          {entity.name}
        </p>
        {entity.theme && <p className="font-mono text-[11px] text-ash">{entity.theme}</p>}
      </div>

      {/* Sentiment badge */}
      <span
        className="shrink-0 rounded px-2 py-[3px] font-mono text-[10px] uppercase tracking-[0.8px]"
        style={{ color: sColor, backgroundColor: `${sColor}14` }}
      >
        {sLabel}
      </span>

      {/* Mention count */}
      <div className="shrink-0 text-right">
        <span className="font-mono text-[16px] font-semibold text-sinal-white">
          {entity.mention_count.toLocaleString("pt-BR")}
        </span>
        <p className="font-mono text-[10px] uppercase tracking-[0.5px] text-[#4A4A56]">mencoes</p>
      </div>

      {/* Arrow if linkable */}
      {entity.slug && (
        <span className="shrink-0 font-mono text-[12px] text-ash" aria-hidden="true">
          &rarr;
        </span>
      )}
    </div>
  );

  if (entity.slug) {
    return (
      <Link href={`/startup/${entity.slug}`} aria-label={`Ver startup ${entity.name}`}>
        {inner}
      </Link>
    );
  }

  return <div>{inner}</div>;
}

export default function StartupsPanel({ entities, total }: StartupsPanelProps) {
  return (
    <div id="panel-startups" role="tabpanel" aria-label="Startup Landscape" className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="mb-1 font-display text-[22px] text-sinal-white">Startup Landscape</h2>
          <p className="text-[13px] text-ash">
            Empresas mais mencionadas em sinais, extraidas automaticamente.
          </p>
        </div>
        {total > 0 && (
          <span className="font-mono text-[12px] text-[#4A4A56]">
            {total.toLocaleString("pt-BR")} empresas detectadas
          </span>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[#59FFB4]" aria-hidden="true" />
          <span className="font-mono text-[11px] text-ash">Sentimento positivo</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[#8A8A96]" aria-hidden="true" />
          <span className="font-mono text-[11px] text-ash">Neutro</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[#FF8A59]" aria-hidden="true" />
          <span className="font-mono text-[11px] text-ash">Negativo</span>
        </div>
        <span className="font-mono text-[11px] text-[#4A4A56]">
          Seta indica startup no nosso mapa
        </span>
      </div>

      {/* List */}
      {entities.length > 0 ? (
        <div className="space-y-2">
          {entities.map((entity, i) => (
            <EntityRow key={entity.name} entity={entity} rank={i + 1} />
          ))}
        </div>
      ) : (
        <div className="py-16 text-center">
          <p className="mb-1 text-[15px] text-ash">Nenhuma empresa detectada</p>
          <p className="text-[13px] text-[#4A4A56]">
            Entidades sao extraidas dos sinais coletados pelo agente RADAR.
          </p>
        </div>
      )}
    </div>
  );
}

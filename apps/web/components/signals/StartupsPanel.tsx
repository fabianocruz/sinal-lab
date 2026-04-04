import Link from "next/link";
import type { SignalEntity, Signal } from "@/lib/signal";
import type { Company } from "@/lib/company";

interface StartupsPanelProps {
  entities: SignalEntity[];
  total: number;
  fallbackSignals?: Signal[];
  knownCompanies?: Company[];
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

// Match known companies from the DB against signal text. Much more accurate
// than regex NER because we search for exact company names we already know.
function matchCompaniesAgainstSignals(companies: Company[], signals: Signal[]): SignalEntity[] {
  if (companies.length === 0 || signals.length === 0) return [];

  const results: Array<{
    company: Company;
    count: number;
    sentimentSum: number;
    theme: string;
  }> = [];

  for (const company of companies) {
    const nameLower = company.name.toLowerCase();
    // Skip very short names (3 chars or fewer) to avoid false positives
    if (nameLower.length <= 3) continue;

    let count = 0;
    let sentimentSum = 0;
    let lastTheme = "";

    for (const signal of signals) {
      const textLower = signal.text.toLowerCase();
      if (textLower.includes(nameLower)) {
        count++;
        sentimentSum += signal.sentiment ?? 0;
        if (signal.theme) lastTheme = signal.theme;
      }
    }

    if (count > 0) {
      results.push({ company, count, sentimentSum, theme: lastTheme });
    }
  }

  return results
    .sort((a, b) => b.count - a.count)
    .slice(0, 30)
    .map((r) => ({
      name: r.company.name,
      slug: r.company.slug,
      theme: r.theme || r.company.sector || "",
      mention_count: r.count,
      sentiment: r.count > 0 ? r.sentimentSum / r.count : 0,
    }));
}

// Derive rough entity list from signals when the /entities endpoint returns nothing.
// Looks for capitalized consecutive words (2-3 tokens) that repeat across signals.
function deriveEntitiesFromSignals(signals: Signal[]): SignalEntity[] {
  const counts = new Map<string, { count: number; sentimentSum: number; theme: string }>();

  for (const signal of signals) {
    // Extract sequences of 2-3 capitalized words (naive NER)
    const matches = signal.text.match(/(?:[A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})/g) ?? [];
    // Also check if signal has an `entities` field (sometimes the API sends it inline)
    const inlineEntities: Array<{ name: string; type: string }> =
      (signal as unknown as { entities?: Array<{ name: string; type: string }> }).entities ?? [];

    const names = [
      ...matches,
      ...inlineEntities.filter((e) => e.type === "company").map((e) => e.name),
    ];

    for (const name of names) {
      if (name.length < 4 || name.length > 50) continue;
      const existing = counts.get(name);
      if (existing) {
        existing.count++;
        existing.sentimentSum += signal.sentiment ?? 0;
      } else {
        counts.set(name, { count: 1, sentimentSum: signal.sentiment ?? 0, theme: signal.theme });
      }
    }
  }

  return Array.from(counts.entries())
    .filter(([, v]) => v.count >= 2) // only names that appear in 2+ signals
    .sort(([, a], [, b]) => b.count - a.count)
    .slice(0, 30)
    .map(([name, v]) => ({
      name,
      slug: null,
      theme: v.theme,
      mention_count: v.count,
      sentiment: v.sentimentSum / v.count,
    }));
}

export default function StartupsPanel({
  entities,
  total,
  fallbackSignals = [],
  knownCompanies = [],
}: StartupsPanelProps) {
  // Priority: 1) /entities API, 2) DB company matching, 3) regex NER fallback
  const companyMatches = matchCompaniesAgainstSignals(knownCompanies, fallbackSignals);

  const displayEntities =
    entities.length > 0
      ? entities
      : companyMatches.length > 0
        ? companyMatches
        : deriveEntitiesFromSignals(fallbackSignals);
  const displayTotal = entities.length > 0 ? total : displayEntities.length;
  const isFallback = entities.length === 0 && displayEntities.length > 0;

  return (
    <div id="panel-startups" role="tabpanel" aria-label="Startup Landscape" className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="mb-1 font-display text-[22px] text-sinal-white">Startup Landscape</h2>
          <p className="text-[13px] text-ash">
            Empresas mais mencionadas em sinais, extraidas automaticamente.
          </p>
          {isFallback && (
            <p className="mt-1 font-mono text-[11px] text-[#4A4A56]">
              Extraidas dos textos dos sinais. Atualizado semanalmente pelo agente RADAR.
            </p>
          )}
        </div>
        {displayTotal > 0 && (
          <span className="font-mono text-[12px] text-[#4A4A56]">
            {displayTotal.toLocaleString("pt-BR")} empresas detectadas
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
      {displayEntities.length > 0 ? (
        <div className="space-y-2">
          {displayEntities.map((entity, i) => (
            <EntityRow key={entity.name} entity={entity} rank={i + 1} />
          ))}
        </div>
      ) : (
        <div className="py-16 text-center">
          <p className="mb-1 text-[15px] text-ash">Nenhuma empresa detectada ainda.</p>
          <p className="text-[13px] text-[#4A4A56]">
            Entidades sao extraidas dos sinais coletados pelo agente RADAR. Atualizado semanalmente.
          </p>
        </div>
      )}
    </div>
  );
}

import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Changelog dos Agentes",
  description:
    "Histórico de mudanças nos agentes de IA do Sinal. Transparência sobre como nossos agentes evoluem.",
};

const CHANGELOG_ENTRIES = [
  {
    date: "2026-03-30",
    agent: "MERCADO",
    color: "#C459FF",
    version: "0.2.0",
    changes: [
      "Expandido de 5 para 21 cidades LATAM (incluindo Santiago, Lima, Montevidéu, Medellín)",
      "Cross-run dedup: empresas já indexadas não aparecem como 'novas' em edições futuras",
      "Filtros de qualidade mais rigorosos (score > 0.4, blocklist expandida para agências, empresas júnior)",
      "Modo snapshot: relatórios analíticos do ecossistema quando não há descobertas novas",
    ],
  },
  {
    date: "2026-03-30",
    agent: "COVERS",
    color: "#E8FF59",
    version: "1.1.0",
    changes: [
      "Art direction atualizado: fundo obrigatoriamente escuro, close-ups cinematográficos",
      "3 variações por cover (era 1), curador escolhe a melhor",
      "Overlay melhorado: badges maiores, gradient quadrático, tipografia mais forte",
      "BAD list: genérico proibido (escritórios, salas de reunião, stock photos)",
    ],
  },
  {
    date: "2026-03-24",
    agent: "SINTESE",
    color: "#E8FF59",
    version: "0.2.0",
    changes: [
      "Coleta de 900+ sinais por edição (era ~300)",
      "42 fontes monitoradas (era 15)",
      "Score de confiança grade A consistente (DQ 4.8/5)",
    ],
  },
  {
    date: "2026-03-16",
    agent: "FUNDING",
    color: "#FF8A59",
    version: "0.1.0",
    changes: [
      "Lançamento do agent de rastreamento de investimentos LATAM",
      "Cobertura inicial: LatamList como fonte primária",
      "Análise editorial com contexto de mercado para cada rodada",
    ],
  },
  {
    date: "2026-03-05",
    agent: "RADAR",
    color: "#59FFB4",
    version: "0.1.0",
    changes: [
      "Lançamento do agent de detecção de tendências",
      "Fontes: Hacker News, arXiv, GitHub Trending, Google Trends",
      "Classificação por momentum e relevância LATAM",
    ],
  },
  {
    date: "2026-02-22",
    agent: "CODIGO",
    color: "#59B4FF",
    version: "0.1.0",
    changes: [
      "Lançamento do agent de ecossistema dev",
      "Monitoramento de PyPI, npm, InfoQ, Dev.to, GitHub Releases",
      "Análise de relevância para times técnicos no Brasil",
    ],
  },
];

export default function ChangelogPage() {
  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-[720px] px-6 py-16 md:px-10">
          <h1 className="font-display text-[clamp(28px,4vw,40px)] leading-[1.15] text-sinal-white">
            Changelog dos Agentes
          </h1>
          <p className="mt-4 text-[16px] leading-relaxed text-silver">
            Registro público de todas as mudanças nos agentes de IA do Sinal. Transparência sobre
            como coletamos, processamos e publicamos inteligência.
          </p>

          <div className="mt-12 space-y-8">
            {CHANGELOG_ENTRIES.map((entry, i) => (
              <article
                key={`${entry.agent}-${entry.date}-${i}`}
                className="rounded-xl border border-[rgba(255,255,255,0.04)] bg-sinal-graphite p-6"
              >
                <div className="mb-3 flex flex-wrap items-center gap-3">
                  <span
                    className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider"
                    style={{
                      color: entry.color,
                      backgroundColor: `${entry.color}10`,
                    }}
                  >
                    <span
                      className="inline-block h-[5px] w-[5px] rounded-full"
                      style={{ backgroundColor: entry.color }}
                    />
                    {entry.agent}
                  </span>
                  <span className="font-mono text-[11px] text-ash">v{entry.version}</span>
                  <span className="font-mono text-[11px] text-ash">{entry.date}</span>
                </div>
                <ul className="space-y-1.5">
                  {entry.changes.map((change, j) => (
                    <li
                      key={j}
                      className="flex items-start gap-2 text-[14px] leading-relaxed text-silver"
                    >
                      <span className="mt-[8px] block h-[4px] w-[4px] shrink-0 rounded-full bg-ash/50" />
                      {change}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

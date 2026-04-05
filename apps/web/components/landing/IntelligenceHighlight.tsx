import Link from "next/link";

const REPORTS = [
  {
    title: "Healthtech + AI: O Mapa Completo do Mercado Global",
    description:
      "100 empresas analisadas, 16 segmentos, 50+ investidores, rankings e 10 tendências para 2026-2028.",
    slug: "healthtech-ai-mapa-completo-mercado-global",
    stats: { companies: "100", segments: "16", investors: "50+" },
    accent: "#59FFB4",
  },
  {
    title: "DevTools Market Intelligence: Top 100 Startups",
    description:
      "100 startups mapeadas, 13 categorias, $30B+ em capital. O maior levantamento de developer tools do ecossistema global.",
    slug: "devtools-market-intelligence-mar-2026",
    stats: { companies: "100", segments: "13", investors: "$30B+" },
    accent: "#59B4FF",
  },
  {
    title: "Embedded Finance: Deep Market Intelligence 2026",
    description:
      "Panorama global de embedded finance: pagamentos, BaaS, lending, insurance. AI transformando infraestrutura financeira. Oportunidades LATAM.",
    slug: "embedded-finance-deep-research-2026",
    stats: { companies: "50+", segments: "8", investors: "$7T" },
    accent: "#FF8A59",
  },
];

export default function IntelligenceHighlight() {
  return (
    <section className="border-b border-[rgba(255,255,255,0.04)] py-section">
      <div className="mx-auto max-w-container px-6 md:px-10">
        {/* Section label */}
        <div className="mb-4 flex items-center gap-2.5">
          <span className="block h-px w-6 bg-[#59B4FF]" />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-[#59B4FF]">
            Intelligence Reports
          </span>
        </div>

        <h2 className="mb-5 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
          Pesquisa profunda, <span style={{ color: "#59B4FF" }}>dados verificáveis.</span>
        </h2>
        <p className="mb-14 max-w-[600px] text-[17px] leading-[1.7] text-ash">
          Deep Studies com centenas de empresas analisadas, scoring proprietário e análise crítica.
          Disponíveis para assinantes com base de dados para download.
        </p>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {REPORTS.map((report) => (
            <Link
              key={report.slug}
              href={`/intelligence/${report.slug}`}
              className="group rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-8 transition-all duration-300 hover:-translate-y-[3px]"
              style={{ borderTop: `4px solid ${report.accent}` }}
            >
              {/* Badge */}
              <span
                className="mb-4 inline-block rounded-md px-3 py-1.5 font-mono text-[11px] font-bold uppercase tracking-[1.5px]"
                style={{ backgroundColor: report.accent, color: "#0A0A0B" }}
              >
                Deep Study
              </span>

              <h3 className="mb-3 font-display text-[20px] leading-[1.25] text-sinal-white group-hover:text-signal transition-colors">
                {report.title}
              </h3>

              <p className="mb-6 text-[14px] leading-relaxed text-ash">{report.description}</p>

              {/* Stats */}
              <div className="flex gap-4">
                {Object.entries(report.stats).map(([key, value]) => (
                  <div key={key} className="text-center">
                    <div className="font-mono text-[18px] font-bold text-sinal-white">{value}</div>
                    <div className="font-mono text-[10px] uppercase tracking-wider text-ash">
                      {key === "companies"
                        ? "empresas"
                        : key === "segments"
                          ? "segmentos"
                          : "capital"}
                    </div>
                  </div>
                ))}
              </div>
            </Link>
          ))}
        </div>

        {/* CTA */}
        <div className="mt-10 text-center">
          <Link
            href="/intelligence"
            className="inline-flex items-center gap-2 font-mono text-[13px] text-[#59B4FF] transition-colors hover:text-sinal-white"
          >
            Ver todos os reports &rarr;
          </Link>
        </div>
      </div>
    </section>
  );
}

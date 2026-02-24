import Link from "next/link";
import { fetchCompanies } from "@/lib/api";
import type { Company } from "@/lib/company";
import { getAccentColor, getCountryFlag, formatFunding } from "@/lib/company";

const SECTOR_PILLS = ["AI / ML", "Fintech", "SaaS", "Healthtech", "Logistics", "Agritech"];

const COUNTRY_STATS = [
  { flag: "\u{1F1E7}\u{1F1F7}", name: "Brasil", pct: 40 },
  { flag: "\u{1F1F2}\u{1F1FD}", name: "M\u00e9xico", pct: 22 },
  { flag: "\u{1F1E8}\u{1F1F4}", name: "Col\u00f4mbia", pct: 16 },
  { flag: "\u{1F1E6}\u{1F1F7}", name: "Argentina", pct: 12 },
  { flag: "\u{1F1E8}\u{1F1F1}", name: "Chile", pct: 10 },
];

const SECTOR_STATS = [
  { name: "Fintech", pct: 100, color: "#FF8A59" },
  { name: "AI / ML", pct: 77, color: "#59B4FF" },
  { name: "SaaS", pct: 61, color: "#C459FF" },
  { name: "E-Commerce", pct: 44, color: "#59FFB4" },
  { name: "Healthtech", pct: 33, color: "#8A8A96" },
];

function MiniCard({ company }: { company: Company }) {
  const accentColor = getAccentColor(company.funding_stage, company.sector);
  const flag = getCountryFlag(company.country);
  const funding = formatFunding(company.total_funding_usd);
  const description = company.short_description || company.description?.slice(0, 120) || null;

  return (
    <Link
      href={`/startup/${company.slug}`}
      className="group block overflow-hidden rounded-xl border border-sinal-slate bg-sinal-graphite transition-all duration-300 hover:-translate-y-[3px] hover:border-[rgba(255,255,255,0.10)] hover:shadow-[0_12px_40px_rgba(0,0,0,0.4)]"
    >
      {/* Stage accent */}
      <div
        className="h-[2px] opacity-50 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `linear-gradient(90deg, ${accentColor}, transparent)`,
        }}
      />

      <div className="px-[18px] pb-4 pt-[18px]">
        {/* Header */}
        <div className="mb-2.5 flex items-start gap-2.5">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] font-display text-[16px]"
            style={{
              background: `linear-gradient(135deg, ${accentColor}18, ${accentColor}08)`,
              border: `1px solid ${accentColor}25`,
              color: accentColor,
            }}
          >
            {company.name.charAt(0)}
          </div>

          <div className="min-w-0 flex-1">
            <div className="mb-0.5 flex items-center gap-1.5">
              <span className="truncate font-display text-[15px] leading-[1.2] text-sinal-white">
                {company.name}
              </span>
              {company.is_trending && (
                <span className="shrink-0 rounded-[3px] bg-[rgba(232,255,89,0.08)] px-[5px] py-px font-mono text-[8px] font-semibold uppercase tracking-[1px] text-signal">
                  NEW
                </span>
              )}
            </div>
            <div className="flex items-center gap-[3px] font-mono text-[10px] text-ash">
              <span>{flag}</span>
              <span>{company.city}</span>
            </div>
          </div>

          {/* Sector pill */}
          {company.sector && (
            <span className="shrink-0 rounded bg-[rgba(255,255,255,0.06)] px-[7px] py-[3px] font-mono text-[9px] tracking-[0.3px] text-ash">
              {company.sector}
            </span>
          )}
        </div>

        {/* Description */}
        {description && (
          <p className="mb-3 line-clamp-2 text-[12.5px] leading-[1.5] text-silver">{description}</p>
        )}

        {/* Footer stats */}
        <div className="flex items-center gap-4 border-t border-[rgba(255,255,255,0.06)] pt-2.5">
          <span className="font-mono text-[11px] font-semibold" style={{ color: accentColor }}>
            {company.funding_stage ?? company.sector ?? "\u2014"}
          </span>
          {funding && (
            <span className="font-mono text-[11px] font-medium text-sinal-white">{funding}</span>
          )}
        </div>
      </div>
    </Link>
  );
}

function BarStat({ flag, name, pct }: { flag: string; name: string; pct: number }) {
  return (
    <div className="mb-2 flex items-center gap-2.5">
      <span className="w-5 text-center text-[14px]">{flag}</span>
      <span className="w-[70px] text-[12px] text-silver">{name}</span>
      <div className="flex-1 overflow-hidden rounded-[3px] bg-sinal-slate">
        <div
          className="h-1.5 rounded-[3px]"
          style={{
            width: `${pct}%`,
            background: "linear-gradient(90deg, #E8FF59, rgba(232,255,89,0.5))",
          }}
        />
      </div>
    </div>
  );
}

export default async function MapaHighlight() {
  const data = await fetchCompanies({ limit: 6 });
  const companies = data.items;

  if (companies.length === 0) return null;

  return (
    <section className="border-t border-sinal-slate">
      <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] py-[100px]">
        {/* Header */}
        <div className="mb-12 flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-[560px]">
            <div className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[2px] text-agent-mercado">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-agent-mercado" />
              MERCADO
              <span className="text-[#4A4A56]">&middot;</span>
              <span className="text-[#4A4A56]">ATUALIZADO SEMANALMENTE</span>
            </div>
            <h2 className="mb-3.5 font-display text-[clamp(28px,4vw,38px)] leading-[1.2] text-sinal-white">
              O mapa mais completo
              <br />
              de startups da Am&eacute;rica Latina.
            </h2>
            <p className="text-[15px] leading-[1.65] text-ash">
              Ecossistema tech de 5 pa&iacute;ses rastreado por agentes de IA &mdash; enriquecido
              com dados de funding, hiring e atividade em c&oacute;digo. Atualizado toda semana.
            </p>
          </div>

          {/* Sector pills */}
          <div className="flex flex-wrap gap-2">
            {SECTOR_PILLS.map((s) => (
              <span
                key={s}
                className="rounded-md border border-sinal-slate bg-sinal-graphite px-3 py-1.5 font-mono text-[11px] tracking-[0.3px] text-ash"
              >
                {s}
              </span>
            ))}
            <span className="px-3 py-1.5 font-mono text-[11px] tracking-[0.3px] text-[#4A4A56]">
              +4 setores
            </span>
          </div>
        </div>

        {/* Main content: Cards + Sidebar */}
        <div className="grid items-start gap-6 lg:grid-cols-[1fr_280px]">
          {/* Cards grid */}
          <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
            {companies.map((company) => (
              <MiniCard key={company.slug} company={company} />
            ))}
          </div>

          {/* Sidebar */}
          <div className="flex flex-col gap-4">
            {/* Country breakdown */}
            <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
              <p className="mb-4 font-mono text-[9px] uppercase tracking-[1.5px] text-[#4A4A56]">
                Distribui&ccedil;&atilde;o por pa&iacute;s
              </p>
              {COUNTRY_STATS.map((c) => (
                <BarStat key={c.name} flag={c.flag} name={c.name} pct={c.pct} />
              ))}
            </div>

            {/* Sector breakdown */}
            <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
              <p className="mb-3.5 font-mono text-[9px] uppercase tracking-[1.5px] text-[#4A4A56]">
                Top setores
              </p>
              {SECTOR_STATS.map((sector, i) => (
                <div
                  key={sector.name}
                  className={`flex items-center gap-2 py-[7px] ${
                    i < SECTOR_STATS.length - 1 ? "border-b border-[rgba(255,255,255,0.06)]" : ""
                  }`}
                >
                  <div
                    className="h-[5px] w-[5px] shrink-0 rounded-full"
                    style={{ background: sector.color }}
                  />
                  <span className="w-20 text-[12px] text-silver">{sector.name}</span>
                  <div className="flex-1 overflow-hidden rounded-sm bg-sinal-slate">
                    <div
                      className="h-1 rounded-sm opacity-60"
                      style={{
                        width: `${sector.pct}%`,
                        background: sector.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* CTA button */}
            <Link
              href="/startups"
              className="flex items-center justify-center gap-2 rounded-[10px] bg-signal px-6 py-3.5 text-[14px] font-bold tracking-[0.2px] text-sinal-black transition-all duration-200 hover:brightness-110"
            >
              Explorar o mapa completo
              <span className="text-[16px]">&rarr;</span>
            </Link>

            {/* Data provenance */}
            <div className="flex items-center gap-2 px-1">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-agent-radar" />
              <span className="font-mono text-[10px] tracking-[0.3px] text-[#4A4A56]">
                Dados: GitHub &middot; LinkedIn &middot; ABStartups &middot; CoreSignal
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

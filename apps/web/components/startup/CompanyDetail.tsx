import React from "react";
import Link from "next/link";
import type { Company } from "@/lib/company";
import { getAccentColor, getCountryFlag, formatFunding, formatDomain } from "@/lib/company";

interface CompanyDetailProps {
  company: Company;
}

function SideBlock({
  title,
  agentColor,
  children,
}: {
  title: string;
  agentColor?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-sinal-slate bg-sinal-graphite">
      <div className="flex items-center justify-between border-b border-sinal-slate px-[18px] py-3.5">
        <span className="font-mono text-[9px] uppercase tracking-[1.5px] text-[#4A4A56]">
          {title}
        </span>
        {agentColor && (
          <span className="h-[5px] w-[5px] rounded-full" style={{ background: agentColor }} />
        )}
      </div>
      <div className="px-[18px] py-4">{children}</div>
    </div>
  );
}

function getFoundedYear(foundedDate: string | null): string | null {
  if (!foundedDate) return null;
  return foundedDate.slice(0, 4);
}

export default function CompanyDetail({ company }: CompanyDetailProps) {
  const accentColor = getAccentColor(company.funding_stage, company.sector);
  const flag = getCountryFlag(company.country);
  const funding = formatFunding(company.total_funding_usd);
  const foundedYear = getFoundedYear(company.founded_date);

  return (
    <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pb-20 pt-8">
      {/* Breadcrumb */}
      <nav className="mb-8 flex items-center gap-2 font-mono text-[11px] text-[#4A4A56]">
        <Link href="/startups" className="text-ash transition-colors hover:text-sinal-white">
          Mapa de Startups
        </Link>
        <span>/</span>
        {company.sector && (
          <>
            <Link
              href={`/startups?sector=${encodeURIComponent(company.sector)}`}
              className="text-ash transition-colors hover:text-sinal-white"
            >
              {company.sector}
            </Link>
            <span>/</span>
          </>
        )}
        <span className="text-silver">{company.name}</span>
      </nav>

      {/* Hero card */}
      <div className="mb-8 overflow-hidden rounded-2xl border border-sinal-slate bg-sinal-graphite">
        {/* Stage accent bar */}
        <div
          className="h-[3px]"
          style={{
            background: `linear-gradient(90deg, ${accentColor}, transparent 70%)`,
          }}
        />

        <div className="px-9 py-8">
          {/* Top row: Logo + Name + Links */}
          <div className="mb-6 flex flex-wrap items-start gap-5">
            {/* Logo */}
            <div
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl font-display text-[28px]"
              style={{
                background: `linear-gradient(135deg, ${accentColor}18, ${accentColor}08)`,
                border: `1px solid ${accentColor}25`,
                color: accentColor,
              }}
            >
              {company.name.charAt(0)}
            </div>

            <div className="min-w-[200px] flex-1">
              <div className="mb-1.5 flex flex-wrap items-center gap-3">
                <h1 className="font-display text-[32px] leading-[1.1] text-sinal-white">
                  {company.name}
                </h1>
                {company.funding_stage && (
                  <span
                    className="rounded-md px-2.5 py-1 font-mono text-[11px] font-semibold"
                    style={{
                      background: `${accentColor}15`,
                      border: `1px solid ${accentColor}30`,
                      color: accentColor,
                    }}
                  >
                    {company.funding_stage}
                  </span>
                )}
              </div>

              {/* Tagline */}
              {company.short_description && (
                <p className="mb-3 max-w-[600px] text-[15px] leading-[1.5] text-silver">
                  {company.short_description}
                </p>
              )}

              {/* Meta row */}
              <div className="flex flex-wrap items-center gap-4">
                <span className="flex items-center gap-1 font-mono text-[12px] text-ash">
                  {flag} {[company.city, company.country].filter(Boolean).join(", ")}
                </span>
                {foundedYear && (
                  <>
                    <span className="text-[#4A4A56]">&middot;</span>
                    <span className="font-mono text-[12px] text-ash">Fundada em {foundedYear}</span>
                  </>
                )}
                {company.sector && (
                  <>
                    <span className="text-[#4A4A56]">&middot;</span>
                    <span className="rounded bg-[rgba(255,255,255,0.06)] px-2 py-[3px] font-mono text-[10px] text-ash">
                      {company.sector}
                    </span>
                  </>
                )}
                {company.sub_sector && (
                  <span className="rounded bg-[rgba(255,255,255,0.06)] px-2 py-[3px] font-mono text-[10px] text-ash">
                    {company.sub_sector}
                  </span>
                )}
              </div>
            </div>

            {/* External links */}
            <div className="flex shrink-0 gap-2">
              {company.website && (
                <a
                  href={
                    company.website.startsWith("http")
                      ? company.website
                      : `https://${company.website}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 rounded-lg border border-sinal-slate px-3.5 py-2 font-mono text-[11px] text-silver transition-all hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white"
                >
                  {"\u2197"} {formatDomain(company.website)}
                </a>
              )}
              {company.linkedin_url && (
                <a
                  href={
                    company.linkedin_url.startsWith("http")
                      ? company.linkedin_url
                      : `https://${company.linkedin_url}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg border border-sinal-slate px-3.5 py-2 font-mono text-[11px] text-silver transition-all hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white"
                >
                  in
                </a>
              )}
              {company.github_url && (
                <a
                  href={company.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg border border-sinal-slate px-3.5 py-2 font-mono text-[11px] text-silver transition-all hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white"
                >
                  gh
                </a>
              )}
            </div>
          </div>

          {/* Key stats row — only show stats with real data */}
          {(() => {
            const stats: { label: string; value: string; color: string }[] = [];
            if (funding)
              stats.push({ label: "Funding Total", value: funding, color: "text-sinal-white" });
            if (company.team_size)
              stats.push({
                label: "Equipe",
                value: `~${company.team_size}`,
                color: "text-sinal-white",
              });
            stats.push({
              label: "Fontes",
              value: String(company.source_count),
              color: "text-sinal-white",
            });
            if (company.business_model)
              stats.push({ label: "Modelo", value: company.business_model, color: "text-signal" });
            if (foundedYear)
              stats.push({ label: "Fundada", value: foundedYear, color: "text-ash" });
            return (
              <div
                className="grid gap-px overflow-hidden rounded-[10px] bg-sinal-slate"
                style={{ gridTemplateColumns: `repeat(${Math.min(stats.length, 4)}, 1fr)` }}
              >
                {stats.map((s) => (
                  <StatBox key={s.label} label={s.label} value={s.value} color={s.color} />
                ))}
              </div>
            );
          })()}
        </div>
      </div>

      {/* Two column layout */}
      <div className="grid items-start gap-6 lg:grid-cols-[1fr_340px]">
        {/* Left column */}
        <div className="flex flex-col gap-6">
          {/* About */}
          {company.description && (
            <SideBlock title="Sobre">
              <p className="text-[14px] leading-[1.7] text-silver">{company.description}</p>
            </SideBlock>
          )}

          {/* Tags */}
          {company.tags && company.tags.length > 0 && (
            <SideBlock title="Tags">
              <div className="flex flex-wrap gap-1.5">
                {company.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-md border border-[rgba(255,255,255,0.06)] px-3 py-1 font-mono text-[11px] text-ash"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </SideBlock>
          )}

          {/* Minimal data placeholder */}
          {!company.description && (!company.tags || company.tags.length === 0) && (
            <div className="rounded-xl border border-dashed border-sinal-slate px-6 py-8 text-center">
              <p className="mb-1.5 text-[14px] text-silver">Perfil em construção</p>
              <p className="mx-auto max-w-[360px] text-[12px] leading-[1.6] text-[#4A4A56]">
                Nossos agentes estão coletando mais dados sobre esta empresa. Informações serão
                adicionadas automaticamente.
              </p>
              {company.github_url && (
                <a
                  href={company.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-sinal-slate px-4 py-2 font-mono text-[11px] text-silver transition-all hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white"
                >
                  Ver no GitHub {"\u2197"}
                </a>
              )}
            </div>
          )}
        </div>

        {/* Right column (sidebar) */}
        <div className="flex flex-col gap-4">
          {/* Tech stack */}
          {company.tech_stack && company.tech_stack.length > 0 && (
            <SideBlock title="Stack Tecnológico" agentColor="#59B4FF">
              <div className="flex flex-wrap gap-1.5">
                {company.tech_stack.map((tech) => (
                  <span
                    key={tech}
                    className="rounded-md border border-[rgba(89,180,255,0.13)] bg-[rgba(89,180,255,0.06)] px-2.5 py-[5px] font-mono text-[11px] text-silver"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </SideBlock>
          )}

          {/* Data provenance */}
          <div className="rounded-xl border border-sinal-slate bg-sinal-graphite px-[18px] py-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-agent-radar" />
                <span className="font-mono text-[9px] uppercase tracking-[1.5px] text-[#4A4A56]">
                  Proveniência
                </span>
              </div>
              {/* Confidence dots */}
              <div className="flex gap-[3px]">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div
                    key={i}
                    className={`h-1.5 w-1.5 rounded-full ${
                      i <= Math.min(company.source_count, 5) ? "bg-signal" : "bg-sinal-slate"
                    }`}
                  />
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between">
                <span className="font-mono text-[10px] text-[#4A4A56]">Agente</span>
                <span className="font-mono text-[10px] text-agent-mercado">INDEX</span>
              </div>
              <div className="flex justify-between">
                <span className="font-mono text-[10px] text-[#4A4A56]">Fontes</span>
                <span className="font-mono text-[10px] text-ash">{company.source_count}</span>
              </div>
            </div>
          </div>

          {/* Back link */}
          <Link
            href="/startups"
            className="flex items-center justify-center gap-1.5 rounded-lg border border-sinal-slate py-2.5 font-mono text-[11px] text-[#4A4A56] transition-all hover:border-[rgba(255,255,255,0.12)] hover:text-ash"
          >
            {"\u2190"} Voltar ao Mapa
          </Link>
        </div>
      </div>
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-sinal-black px-5 py-4 text-center">
      <div className={`font-display text-[22px] leading-none ${color}`}>{value}</div>
      <div className="mt-1 font-mono text-[9px] uppercase tracking-[1px] text-[#4A4A56]">
        {label}
      </div>
    </div>
  );
}

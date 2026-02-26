import Link from "next/link";
import type { Company } from "@/lib/company";
import { getAccentColor, getCountryFlag, formatFunding, formatDomain } from "@/lib/company";

interface CompanyCardProps {
  company: Company;
}

function isNew(createdAt: string): boolean {
  const created = new Date(createdAt);
  const fourteenDaysAgo = new Date();
  fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);
  return created > fourteenDaysAgo;
}

function getFoundedYear(foundedDate: string | null): string | null {
  if (!foundedDate) return null;
  return foundedDate.slice(0, 4);
}

export default function CompanyCard({ company }: CompanyCardProps) {
  const description = company.short_description || company.description?.slice(0, 150) || null;
  const accentColor = getAccentColor(company.funding_stage, company.sector);
  const flag = getCountryFlag(company.country);
  const foundedYear = getFoundedYear(company.founded_date);
  const funding = formatFunding(company.total_funding_usd);
  const domain = formatDomain(company.website);
  const showNew = isNew(company.created_at);

  return (
    <Link
      href={`/startup/${company.slug}`}
      className="group block overflow-hidden rounded-xl border border-sinal-slate bg-sinal-graphite transition-all duration-300 hover:-translate-y-[2px] hover:border-[rgba(255,255,255,0.10)] hover:shadow-[0_8px_32px_rgba(0,0,0,0.3)]"
      aria-label={`Ver: ${company.name}`}
    >
      {/* Stage color accent bar */}
      <div
        className="h-[2px] opacity-40 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `linear-gradient(90deg, ${accentColor}, transparent)`,
        }}
      />

      <div className="flex flex-col px-5 pb-4 pt-5">
        {/* Header: Logo + Name + Country */}
        <div className="mb-3 flex items-start gap-3">
          {/* Logo initial */}
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] font-display text-lg"
            style={{
              background: `linear-gradient(135deg, ${accentColor}15, ${accentColor}08)`,
              border: `1px solid ${accentColor}20`,
              color: accentColor,
            }}
          >
            {company.name.charAt(0)}
          </div>

          <div className="min-w-0 flex-1">
            <div className="mb-0.5 flex items-center gap-2">
              <h2 className="truncate font-display text-[17px] leading-[1.2] text-sinal-white">
                {company.name}
              </h2>
              {company.is_trending && (
                <span className="shrink-0 rounded bg-[rgba(232,255,89,0.08)] px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-[1px] text-signal">
                  TRENDING
                </span>
              )}
              {showNew && !company.is_trending && (
                <span className="shrink-0 rounded bg-[rgba(89,255,180,0.08)] px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-[1px] text-agent-radar">
                  NEW
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 font-mono text-[11px] text-ash">
              <span>{flag}</span>
              <span>{[company.city, company.country].filter(Boolean).join(", ")}</span>
              {foundedYear && (
                <>
                  <span className="text-[#4A4A56]">&middot;</span>
                  <span>{foundedYear}</span>
                </>
              )}
              {domain && (
                <>
                  <span className="text-[#4A4A56]">&middot;</span>
                  <span className="truncate text-[#4A4A56]">{domain}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Description */}
        {description && (
          <p className="mb-3.5 line-clamp-2 text-[13px] leading-[1.5] text-silver">{description}</p>
        )}

        {/* Tags */}
        {company.tags && company.tags.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-1">
            {company.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded bg-[rgba(255,255,255,0.06)] px-2 py-[3px] font-mono text-[10px] tracking-[0.3px] text-ash"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Bottom stats bar */}
        <div className="mt-auto flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] pt-3">
          {/* Stage */}
          <div className="flex flex-col items-start">
            <span
              className="font-mono text-[13px] font-semibold leading-none"
              style={{ color: accentColor }}
            >
              {company.funding_stage ?? company.sector ?? "—"}
            </span>
            <span className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.5px] text-[#4A4A56]">
              {company.funding_stage ? "Stage" : "Setor"}
            </span>
          </div>

          {/* Funding */}
          {funding && (
            <div className="flex flex-col items-start">
              <span className="font-mono text-[13px] font-semibold leading-none text-sinal-white">
                {funding}
              </span>
              <span className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.5px] text-[#4A4A56]">
                Funding
              </span>
            </div>
          )}

          {/* Team size */}
          {company.team_size != null && (
            <div className="flex flex-col items-start">
              <span className="font-mono text-[13px] font-semibold leading-none text-silver">
                {company.team_size}
              </span>
              <span className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.5px] text-[#4A4A56]">
                Equipe
              </span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

import Link from "next/link";
import type { Company } from "@/lib/company";

interface CompanyCardProps {
  company: Company;
}

export default function CompanyCard({ company }: CompanyCardProps) {
  const displayDescription =
    company.short_description || company.description?.slice(0, 120) || null;

  return (
    <Link
      href={`/startup/${company.slug}`}
      className="group block overflow-hidden rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite transition-all duration-300 hover:-translate-y-[3px] hover:border-[rgba(255,255,255,0.10)]"
      aria-label={`Ver: ${company.name}`}
    >
      <div className="px-[22px] pb-6 pt-5">
        {/* Sector badge + source count */}
        <div className="mb-3 flex items-center justify-between">
          {company.sector && (
            <span className="rounded-[5px] bg-[rgba(232,255,89,0.06)] px-2 py-[5px] font-mono text-[9px] uppercase tracking-[1.5px] text-signal">
              {company.sector}
            </span>
          )}
          {company.source_count > 1 && (
            <span className="font-mono text-[10px] text-ash" title="Fontes confirmadas">
              {company.source_count} fontes
            </span>
          )}
        </div>

        {/* Name */}
        <h2 className="mb-2 font-display text-[18px] leading-[1.35] text-sinal-white">
          {company.name}
        </h2>

        {/* Description */}
        {displayDescription && (
          <p className="mb-4 line-clamp-2 text-[14px] leading-[1.5] text-ash">
            {displayDescription}
          </p>
        )}

        {/* Location */}
        {(company.city || company.country) && (
          <div className="mb-3 font-mono text-[12px] tracking-[0.5px] text-ash">
            {[company.city, company.country].filter(Boolean).join(", ")}
          </div>
        )}

        {/* Tags */}
        {company.tags && company.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {company.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-md border border-[rgba(255,255,255,0.06)] px-2 py-0.5 font-mono text-[10px] text-ash"
              >
                {tag}
              </span>
            ))}
            {company.tags.length > 3 && (
              <span className="font-mono text-[10px] text-ash">+{company.tags.length - 3}</span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}

import Link from "next/link";
import type { Company } from "@/lib/company";

interface CompanyDetailProps {
  company: Company;
}

export default function CompanyDetail({ company }: CompanyDetailProps) {
  return (
    <article className="mx-auto max-w-[720px] px-6 py-12 md:px-10">
      {/* Back link */}
      <Link
        href="/startups"
        className="mb-8 inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
      >
        &larr; Voltar ao Mapa
      </Link>

      {/* Hero */}
      <header className="mb-10 border-b border-[rgba(255,255,255,0.06)] pb-10">
        {/* Sector + source count */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          {company.sector && (
            <span className="rounded-[5px] bg-[rgba(232,255,89,0.06)] px-2 py-1 font-mono text-[11px] uppercase tracking-[1.5px] text-signal">
              {company.sector}
            </span>
          )}
          {company.sub_sector && (
            <span className="font-mono text-[11px] tracking-[0.5px] text-ash">
              {company.sub_sector}
            </span>
          )}
          {company.source_count > 1 && (
            <span className="rounded-[5px] bg-[rgba(255,255,255,0.04)] px-2 py-1 font-mono text-[10px] text-ash">
              {company.source_count} fontes
            </span>
          )}
        </div>

        {/* Name */}
        <h1 className="font-display text-[clamp(24px,4vw,36px)] leading-[1.2] text-sinal-white">
          {company.name}
        </h1>

        {/* Location */}
        {(company.city || company.country) && (
          <p className="mt-2 font-mono text-[13px] text-ash">
            {[company.city, company.state, company.country].filter(Boolean).join(", ")}
          </p>
        )}

        {/* Description */}
        {company.description && (
          <p className="mt-4 text-[16px] leading-relaxed text-silver">{company.description}</p>
        )}
      </header>

      {/* Details grid */}
      <section className="mb-10">
        <h2 className="mb-4 font-mono text-[12px] uppercase tracking-[1.5px] text-ash">Detalhes</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {company.founded_date && <DetailItem label="Fundada" value={company.founded_date} />}
          {company.team_size && <DetailItem label="Equipe" value={`~${company.team_size}`} />}
          {company.business_model && <DetailItem label="Modelo" value={company.business_model} />}
        </div>
      </section>

      {/* Tech stack */}
      {company.tech_stack && company.tech_stack.length > 0 && (
        <section className="mb-10">
          <h2 className="mb-4 font-mono text-[12px] uppercase tracking-[1.5px] text-ash">
            Tech Stack
          </h2>
          <div className="flex flex-wrap gap-2">
            {company.tech_stack.map((tech) => (
              <span
                key={tech}
                className="rounded-lg border border-[rgba(89,180,255,0.2)] bg-[rgba(89,180,255,0.06)] px-3 py-1.5 font-mono text-[11px] text-[#59B4FF]"
              >
                {tech}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Tags */}
      {company.tags && company.tags.length > 0 && (
        <section className="mb-10">
          <h2 className="mb-4 font-mono text-[12px] uppercase tracking-[1.5px] text-ash">Tags</h2>
          <div className="flex flex-wrap gap-2">
            {company.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-md border border-[rgba(255,255,255,0.06)] px-3 py-1 font-mono text-[11px] text-ash"
              >
                {tag}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* External links */}
      {(company.website || company.github_url || company.linkedin_url || company.twitter_url) && (
        <section className="mb-10">
          <h2 className="mb-4 font-mono text-[12px] uppercase tracking-[1.5px] text-ash">Links</h2>
          <div className="flex flex-wrap gap-3">
            {company.website && <ExternalLink href={company.website} label="Website" />}
            {company.github_url && <ExternalLink href={company.github_url} label="GitHub" />}
            {company.linkedin_url && <ExternalLink href={company.linkedin_url} label="LinkedIn" />}
            {company.twitter_url && <ExternalLink href={company.twitter_url} label="Twitter" />}
          </div>
        </section>
      )}

      {/* Footer */}
      <div className="mt-12 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-6">
        <p className="font-mono text-[12px] text-ash">
          <strong className="text-bone">Sinal</strong> rastreia startups LATAM via agentes de IA com
          verificacao multi-fonte.{" "}
          <Link href="/#metodologia" className="text-signal underline underline-offset-2">
            Metodologia
          </Link>
        </p>
      </div>

      <div className="mt-8">
        <Link
          href="/startups"
          className="inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
        >
          &larr; Ver todas as startups
        </Link>
      </div>
    </article>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-4">
      <dt className="mb-1 font-mono text-[10px] uppercase tracking-[1px] text-ash">{label}</dt>
      <dd className="font-body text-[14px] text-sinal-white">{value}</dd>
    </div>
  );
}

function ExternalLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-2.5 font-mono text-[12px] text-ash transition-all duration-200 hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white"
    >
      {label}
      <span aria-hidden="true">&nearr;</span>
    </a>
  );
}

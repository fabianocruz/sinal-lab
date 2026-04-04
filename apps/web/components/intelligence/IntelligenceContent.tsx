import Link from "next/link";
import MarkdownRenderer from "@/components/newsletter/MarkdownRenderer";
import HeroImage from "@/components/newsletter/HeroImage";
import SourcesList from "@/components/newsletter/SourcesList";
import type { ContentApiItem } from "@/lib/newsletter";

interface IntelligenceContentProps {
  item: ContentApiItem;
}

const ACCENT_COLOR = "#59B4FF";

export default function IntelligenceContent({ item }: IntelligenceContentProps) {
  const dateStr = item.published_at
    ? new Date(item.published_at).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      })
    : "";

  const body = item.body_md ?? "";

  return (
    <article className="mx-auto max-w-[720px] px-6 py-12 md:px-10">
      {/* Back link */}
      <Link
        href="/intelligence"
        className="mb-8 inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
      >
        &larr; Voltar aos Relatorios
      </Link>

      {/* Hero cover image */}
      <HeroImage hero_image={item.metadata_?.hero_image} agentColor={ACCENT_COLOR} />

      {/* Report header */}
      <header className="mb-10 border-b border-[rgba(255,255,255,0.06)] pb-10">
        <div className="mb-4 flex items-center gap-3">
          <span
            className="rounded-[5px] px-[10px] py-[5px] font-mono text-[9px] font-semibold uppercase tracking-[1.5px]"
            style={{
              backgroundColor: "rgba(89,180,255,0.06)",
              color: ACCENT_COLOR,
            }}
          >
            Intelligence
          </span>
          {dateStr && (
            <span className="font-mono text-[11px] tracking-[0.5px] text-ash">{dateStr}</span>
          )}
        </div>

        <h1 className="font-display text-[clamp(24px,4vw,36px)] leading-[1.2] text-sinal-white">
          {item.title}
        </h1>

        {item.subtitle && (
          <p className="mt-4 text-[16px] leading-relaxed text-silver">{item.subtitle}</p>
        )}

        {/* Author info */}
        <div className="mt-6 flex items-center gap-3">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-mono text-[11px] font-semibold"
            style={{ backgroundColor: "rgba(89,180,255,0.15)", color: ACCENT_COLOR }}
            aria-hidden="true"
          >
            {(item.author_name ?? "Sinal Intelligence").charAt(0)}&middot;
          </div>
          <div>
            <p className="text-[13px] font-semibold text-bone">
              {item.author_name ?? "Sinal Intelligence"}
            </p>
            <p className="text-[12px] text-ash">Market Intelligence</p>
          </div>
        </div>
        {/* Download button */}
        {item.metadata_?.download_url && (
          <a
            href={item.metadata_.download_url}
            download
            className="mt-6 inline-flex items-center gap-2 rounded-lg border border-[rgba(89,180,255,0.2)] bg-[rgba(89,180,255,0.06)] px-5 py-3 font-mono text-[13px] font-semibold transition-colors hover:bg-[rgba(89,180,255,0.12)]"
            style={{ color: ACCENT_COLOR }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M8 1v10m0 0L4.5 7.5M8 11l3.5-3.5M2 13h12"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {item.metadata_.download_label || "Download dados (Excel)"}
          </a>
        )}
      </header>

      {/* Full content — no gating for intelligence reports */}
      <div className="prose-sinal">
        <MarkdownRenderer content={body} agentColor={ACCENT_COLOR} />
      </div>

      {/* Sources */}
      {item.sources && item.sources.length > 0 && (
        <SourcesList sources={item.sources} agentColor={ACCENT_COLOR} />
      )}

      {/* Footer */}
      <div className="mt-12">
        <Link
          href="/intelligence"
          className="inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
        >
          &larr; Ver todos os relatorios
        </Link>
      </div>
    </article>
  );
}

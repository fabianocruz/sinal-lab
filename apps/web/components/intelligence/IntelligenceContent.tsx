import Link from "next/link";
import MarkdownRenderer from "@/components/newsletter/MarkdownRenderer";
import HeroImage from "@/components/newsletter/HeroImage";
import SourcesList from "@/components/newsletter/SourcesList";
import DownloadButton from "@/components/intelligence/DownloadButton";
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
            className="rounded-[5px] px-[10px] py-[5px] font-mono text-[11px] font-semibold uppercase tracking-[1.5px]"
            style={{
              backgroundColor: "rgba(89,180,255,0.06)",
              color: ACCENT_COLOR,
            }}
          >
            Intelligence
          </span>
          {dateStr && (
            <span className="font-mono text-[12px] tracking-[0.5px] text-ash">{dateStr}</span>
          )}
        </div>

        <h1 className="font-display text-[clamp(24px,4vw,36px)] leading-[1.2] text-sinal-white">
          {item.title}
        </h1>

        {item.subtitle && (
          <p className="mt-4 text-[18px] leading-relaxed text-silver">{item.subtitle}</p>
        )}

        {/* Author info */}
        <div className="mt-6 flex items-center gap-3">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-mono text-[12px] font-semibold"
            style={{ backgroundColor: "rgba(89,180,255,0.15)", color: ACCENT_COLOR }}
            aria-hidden="true"
          >
            {(item.author_name ?? "Sinal Intelligence").charAt(0)}&middot;
          </div>
          <div>
            <p className="text-[14px] font-semibold text-bone">
              {item.author_name ?? "Sinal Intelligence"}
            </p>
            <p className="text-[13px] text-ash">Market Intelligence</p>
          </div>
        </div>
        {/* Download button — gated behind auth */}
        {item.metadata_?.download_url && (
          <DownloadButton
            downloadUrl={item.metadata_.download_url}
            label={item.metadata_.download_label || "Download dados (Excel)"}
          />
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

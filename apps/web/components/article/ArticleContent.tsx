"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import MarkdownRenderer from "@/components/newsletter/MarkdownRenderer";
import SourcesList from "@/components/newsletter/SourcesList";
import GatedOverlay from "@/components/newsletter/GatedOverlay";
import type { ContentApiItem } from "@/lib/newsletter";

interface ArticleContentProps {
  item: ContentApiItem;
}

const ACCENT_COLOR = "#E8FF59";

export default function ArticleContent({ item }: ArticleContentProps) {
  const { status } = useSession();
  const isAuthenticated = status === "authenticated";

  const dateStr = item.published_at
    ? new Date(item.published_at).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      })
    : "";

  const body = item.body_md ?? "";
  const blocks = body.split("\n\n").filter((p) => p.trim().length > 0);
  const previewCount = Math.ceil(blocks.length * 0.3);
  const previewMd = blocks.slice(0, previewCount).join("\n\n");
  const gatedMd = blocks.slice(previewCount).join("\n\n");

  return (
    <article className="mx-auto max-w-[720px] px-6 py-12 md:px-10">
      {/* Back link */}
      <Link
        href="/artigos"
        className="mb-8 inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
      >
        &larr; Voltar aos Artigos
      </Link>

      {/* Article header */}
      <header className="mb-10 border-b border-[rgba(255,255,255,0.06)] pb-10">
        <div className="mb-4 flex items-center gap-3">
          <span className="rounded-[5px] bg-[rgba(232,255,89,0.06)] px-[10px] py-[5px] font-mono text-[9px] font-semibold uppercase tracking-[1.5px] text-signal">
            Artigo
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
      </header>

      {/* Preview content — always visible */}
      <div className="prose-sinal">
        <MarkdownRenderer content={previewMd} agentColor={ACCENT_COLOR} />
      </div>

      {/* Gated content or remaining body */}
      {gatedMd && (
        <>
          {isAuthenticated ? (
            <div className="prose-sinal mt-0">
              <MarkdownRenderer content={gatedMd} agentColor={ACCENT_COLOR} />
            </div>
          ) : (
            <GatedOverlay />
          )}
        </>
      )}

      {/* Sources — visible when full content is accessible */}
      {(isAuthenticated || !gatedMd) && item.sources && item.sources.length > 0 && (
        <SourcesList sources={item.sources} agentColor={ACCENT_COLOR} />
      )}

      {/* Footer */}
      {(isAuthenticated || !gatedMd) && (
        <div className="mt-12">
          <Link
            href="/artigos"
            className="inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
          >
            &larr; Ver todos os artigos
          </Link>
        </div>
      )}

      {/* Back link for unauthenticated users */}
      {!isAuthenticated && gatedMd && (
        <div className="mt-8">
          <Link
            href="/artigos"
            className="inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
          >
            &larr; Ver todos os artigos
          </Link>
        </div>
      )}
    </article>
  );
}

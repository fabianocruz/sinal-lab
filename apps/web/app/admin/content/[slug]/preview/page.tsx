"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import MarkdownRenderer from "@/components/newsletter/MarkdownRenderer";
import { adminGetContent, type AdminContent } from "@/lib/admin-api";

export default function PreviewContentPage() {
  const params = useParams<{ slug: string }>();
  const [content, setContent] = useState<AdminContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await adminGetContent(params.slug);
        setContent(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro ao carregar");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.slug]);

  if (loading) {
    return <p className="py-8 font-mono text-[13px] text-ash">Carregando preview...</p>;
  }

  if (error || !content) {
    return (
      <p className="py-8 font-mono text-[13px] text-[#FF5959]">
        {error ?? "Conteudo nao encontrado."}
      </p>
    );
  }

  return (
    <div>
      {/* Admin bar */}
      <div className="mb-6 flex items-center gap-4 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-3">
        <span className="font-mono text-[11px] uppercase tracking-[1px] text-ash">Preview</span>
        <span
          className={`rounded-md px-2 py-0.5 font-mono text-[11px] ${
            content.review_status === "published"
              ? "bg-[rgba(89,255,180,0.15)] text-[#59FFB4]"
              : "bg-[rgba(255,255,255,0.08)] text-ash"
          }`}
        >
          {content.review_status}
        </span>
        <div className="flex-1" />
        <Link
          href={`/admin/content/${params.slug}/edit`}
          className="font-mono text-[12px] text-signal hover:underline"
        >
          Editar
        </Link>
        <Link href="/admin/content" className="font-mono text-[12px] text-ash hover:text-bone">
          Voltar
        </Link>
      </div>

      {/* Preview content (matches newsletter page layout) */}
      <article className="mx-auto max-w-[720px]">
        <h1 className="mb-4 font-display text-[32px] leading-[1.25] text-sinal-white md:text-[40px]">
          {content.title}
        </h1>

        {content.subtitle && (
          <p className="mb-6 text-[16px] leading-[1.6] text-ash">{content.subtitle}</p>
        )}

        <div className="mb-4 font-mono text-[12px] text-ash">
          {content.content_type} &middot; {content.review_status}
          {content.published_at &&
            ` · ${new Date(content.published_at).toLocaleDateString("pt-BR")}`}
        </div>

        <hr className="mb-8 border-[rgba(255,255,255,0.06)]" />

        <MarkdownRenderer content={content.body_md} />

        {content.sources && content.sources.length > 0 && (
          <div className="mt-8 border-t border-[rgba(255,255,255,0.06)] pt-6">
            <h3 className="mb-3 font-mono text-[11px] uppercase tracking-[1.5px] text-ash">
              Fontes
            </h3>
            <ul className="space-y-1">
              {content.sources.map((src, i) => (
                <li key={i}>
                  <a
                    href={src}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-[13px] text-signal underline underline-offset-2 hover:text-signal-dim"
                  >
                    {(() => {
                      try {
                        return new URL(src).hostname;
                      } catch {
                        return src;
                      }
                    })()}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </article>
    </div>
  );
}

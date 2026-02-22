import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import MarkdownRenderer from "@/components/newsletter/MarkdownRenderer";
import SourcesList from "@/components/newsletter/SourcesList";
import { fetchNewsletterBySlug } from "@/lib/api";

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const item = await fetchNewsletterBySlug(params.slug);
  if (!item) return { title: "Artigo nao encontrado" };

  return {
    title: item.title,
    description: item.subtitle ?? item.summary ?? item.meta_description ?? "",
    openGraph: {
      title: item.title,
      description: item.subtitle ?? item.summary ?? "",
      type: "article",
      publishedTime: item.published_at ?? undefined,
    },
  };
}

export default async function ArticleSlugPage({ params }: PageProps) {
  const item = await fetchNewsletterBySlug(params.slug);
  if (!item) notFound();

  const dateStr = item.published_at
    ? new Date(item.published_at).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      })
    : "";

  const accentColor = "#E8FF59";

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
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

          {/* Article body */}
          <div className="prose-sinal">
            <MarkdownRenderer content={item.body_md ?? ""} agentColor={accentColor} />
          </div>

          {/* Sources */}
          {item.sources && item.sources.length > 0 && (
            <SourcesList sources={item.sources} agentColor={accentColor} />
          )}

          {/* Footer */}
          <div className="mt-12">
            <Link
              href="/artigos"
              className="inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
            >
              &larr; Ver todos os artigos
            </Link>
          </div>
        </article>
      </main>
      <Footer />
    </>
  );
}

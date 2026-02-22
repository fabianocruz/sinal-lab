import type { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Pagination from "@/components/newsletter/Pagination";
import { fetchArticles } from "@/lib/api";
import { CARD_GRADIENTS } from "@/lib/newsletter";

export const metadata: Metadata = {
  title: "Artigos",
  description: "Artigos e analises originais sobre o ecossistema tech da America Latina.",
  openGraph: {
    title: "Artigos | Sinal",
    description: "Artigos e analises originais sobre o ecossistema tech da America Latina.",
    type: "website",
  },
};

const PAGE_SIZE = 9;

export default async function ArtigosPage({ searchParams }: { searchParams: { page?: string } }) {
  const page = parseInt(searchParams.page ?? "1", 10);
  const offset = (page - 1) * PAGE_SIZE;

  const data = await fetchArticles({ limit: PAGE_SIZE, offset });

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-[1120px] px-[clamp(20px,4vw,48px)] py-10">
          {/* Page header */}
          <div className="mb-10">
            <h1 className="font-display text-[clamp(28px,4vw,40px)] text-sinal-white">Artigos</h1>
            <p className="mt-1 text-[15px] text-ash">
              Analises originais e perspectivas sobre o ecossistema tech LATAM.
            </p>
          </div>

          {/* Articles grid */}
          {data.items.length === 0 ? (
            <p className="py-16 text-center font-mono text-[14px] text-ash">
              Nenhum artigo publicado ainda.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((item, index) => {
                const dateStr = item.published_at
                  ? new Date(item.published_at).toLocaleDateString("pt-BR", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })
                  : "";

                const gradientIndex = ((index % 6) + 1) as 1 | 2 | 3 | 4 | 5 | 6;

                return (
                  <Link
                    key={item.id}
                    href={`/artigos/${item.slug}`}
                    className="group block overflow-hidden rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite transition-all duration-300 hover:-translate-y-[3px] hover:border-[rgba(255,255,255,0.10)]"
                    aria-label={`Ler: ${item.title}`}
                  >
                    {/* Gradient image area — matches ArchiveCard aspect ratio */}
                    <div
                      className="relative aspect-[16/10]"
                      style={{ background: CARD_GRADIENTS[gradientIndex] }}
                      aria-hidden="true"
                    >
                      {/* Type badge */}
                      <div className="absolute left-3 top-3 flex items-center gap-[5px] rounded-[5px] bg-[rgba(10,10,11,0.75)] px-[10px] py-[5px] font-mono text-[9px] font-semibold uppercase tracking-[1.5px] text-signal backdrop-blur-[8px]">
                        <span
                          className="inline-block h-[5px] w-[5px] rounded-full bg-signal"
                          aria-hidden="true"
                        />
                        Artigo
                      </div>
                    </div>

                    {/* Body */}
                    <div className="px-[22px] pb-6 pt-5">
                      {/* Meta row */}
                      <div className="mb-3 flex items-center justify-between">
                        <span className="font-mono text-[12px] tracking-[0.5px] text-ash">
                          {dateStr}
                        </span>
                        <span className="flex items-center gap-1 font-mono text-[12px] text-ash">
                          <svg
                            viewBox="0 0 24 24"
                            className="h-[14px] w-[14px]"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            aria-hidden="true"
                          >
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                          </svg>
                          0
                        </span>
                      </div>

                      {/* Title */}
                      <h2 className="mb-2 font-display text-[18px] leading-[1.35] text-sinal-white">
                        {item.title}
                      </h2>

                      {/* Subtitle */}
                      <p className="mb-4 text-[14px] leading-[1.5] text-ash">
                        {item.subtitle ?? item.summary ?? item.meta_description ?? ""}
                      </p>

                      {/* Author footer */}
                      <div className="flex items-center gap-[10px]">
                        <div
                          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-[10px] font-semibold"
                          style={{
                            backgroundColor: "rgba(232,255,89,0.15)",
                            color: "#E8FF59",
                          }}
                          aria-hidden="true"
                        >
                          S&middot;
                        </div>
                        <div className="text-[13px]">
                          <strong className="block text-bone">Sinal Editorial</strong>
                          <span className="text-[12px] text-ash">Redacao</span>
                        </div>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {data.items.length > 0 && <Pagination currentPage={page} totalPages={totalPages} />}
        </div>
      </main>
      <Footer />
    </>
  );
}

import { Suspense } from "react";
import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import FeedItem from "@/components/feed/FeedItem";
import FeedFilterBar from "@/components/feed/FeedFilterBar";
import TrendingSidebar from "@/components/feed/TrendingSidebar";
import Pagination from "@/components/newsletter/Pagination";
import { fetchCuratedFeed, fetchSignalClusters } from "@/lib/api";

// ---------------------------------------------------------------------------
// ISR — refresh every 60 seconds (feed updates frequently)
// ---------------------------------------------------------------------------

export const revalidate = 60;

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

export const metadata: Metadata = {
  title: "Feed | Sinal",
  description:
    "Os sinais mais relevantes sobre AI, Fintech e Banking, selecionados e contextualizados pela editora Ana Torres.",
  openGraph: {
    title: "Feed | Sinal",
    description: "Sinais curados sobre AI, Fintech e Banking. Atualizados em tempo real.",
    type: "website",
  },
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 30;

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function FeedPage({
  searchParams,
}: {
  searchParams: { theme?: string; page?: string };
}) {
  const page = Math.max(1, parseInt(searchParams.page ?? "1", 10));
  const offset = (page - 1) * PAGE_SIZE;
  const theme = searchParams.theme ?? "";

  // Fetch curated feed and clusters in parallel
  const [feedData, clustersData] = await Promise.all([
    fetchCuratedFeed({
      theme: theme || undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    fetchSignalClusters({ limit: 20 }),
  ]);

  const items = feedData.items;
  const totalPages = Math.max(1, Math.ceil(feedData.total / PAGE_SIZE));
  const isCurated = feedData.isCurated;

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        {/* ----------------------------------------------------------------
            Header — dark with subtle signal accent
        ----------------------------------------------------------------- */}
        <div className="border-b border-[rgba(255,255,255,0.04)] bg-sinal-graphite">
          <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] py-10">
            <div className="mb-2 flex items-center gap-2">
              <span
                className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-signal"
                aria-hidden="true"
              />
              <span className="font-mono text-[11px] uppercase tracking-[2px] text-signal">
                Curado em tempo real
              </span>
            </div>
            <h1 className="mb-2 font-display text-[clamp(28px,4vw,40px)] text-sinal-white">Feed</h1>
            <p className="max-w-[500px] text-[15px] leading-[1.6] text-ash">
              Os sinais mais relevantes sobre AI, Fintech e Banking, selecionados e contextualizados
              pela editora Ana Torres.
            </p>
          </div>
        </div>

        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)]">
          {/* ----------------------------------------------------------------
              Filter bar — theme pills only
          ----------------------------------------------------------------- */}
          <div className="mb-8 border-t border-[rgba(255,255,255,0.04)] pt-6">
            <Suspense fallback={<FilterBarFallback />}>
              <FeedFilterBar />
            </Suspense>
          </div>

          {/* ----------------------------------------------------------------
              Active filter banner
          ----------------------------------------------------------------- */}
          {theme && (
            <div className="mb-6 flex items-center gap-2.5 rounded-lg border border-[rgba(232,255,89,0.15)] bg-[rgba(232,255,89,0.04)] px-4 py-2.5">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-signal" aria-hidden="true" />
              <p className="text-[12px] text-silver">
                Filtrando por: <span className="font-semibold text-signal">{theme}</span>
              </p>
            </div>
          )}

          {/* ----------------------------------------------------------------
              Fallback mode notice
          ----------------------------------------------------------------- */}
          {!isCurated && items.length > 0 && (
            <div className="mb-6 flex items-center gap-2.5 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-2.5">
              <span className="font-mono text-[11px] text-ash">
                Exibindo sinais brutos. O curador de feed estara disponivel em breve.
              </span>
            </div>
          )}

          {/* ----------------------------------------------------------------
              Main layout: feed + sidebar
          ----------------------------------------------------------------- */}
          <div className="flex gap-10">
            {/* Feed column */}
            <div className="min-w-0 flex-1">
              {items.length === 0 ? (
                <EmptyState theme={theme} />
              ) : (
                <>
                  <ul aria-label="Feed curado">
                    {items.map((item) => (
                      <li key={item.id}>
                        <FeedItem item={item} />
                      </li>
                    ))}
                  </ul>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="py-8">
                      <Pagination currentPage={page} totalPages={totalPages} basePath="/feed" />
                    </div>
                  )}
                </>
              )}

              {/* Count + attribution */}
              {items.length > 0 && (
                <div className="flex flex-wrap items-center justify-between gap-2 pb-8 pt-4">
                  <p className="font-mono text-[11px] text-[#4A4A56]">
                    Mostrando {offset + 1}&ndash;
                    {Math.min(offset + items.length, feedData.total)} de{" "}
                    {feedData.total.toLocaleString("pt-BR")} itens
                  </p>
                  {isCurated && (
                    <p className="font-mono text-[11px] text-[#4A4A56]">
                      Curado por <span className="text-ash">Ana Torres, Editora de Feed</span>
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Sidebar — hidden on mobile */}
            <div className="hidden w-[280px] shrink-0 lg:block">
              <div className="sticky top-[88px]">
                <TrendingSidebar clusters={clustersData.items} />

                {/* Methodology note */}
                <div className="mt-6 rounded-xl border border-sinal-slate bg-sinal-graphite px-4 py-4">
                  <p className="mb-1 font-mono text-[10px] uppercase tracking-[2px] text-[#4A4A56]">
                    Metodologia
                  </p>
                  <p className="text-[12px] leading-[1.6] text-ash">
                    Sinais coletados pelo agente{" "}
                    <span className="font-mono text-[11px] text-agent-radar">RADAR</span> e curados
                    editorialmente. Atualizado a cada hora.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState({ theme }: { theme: string }) {
  return (
    <div className="py-20 text-center">
      <p className="mb-2 font-mono text-[11px] uppercase tracking-[2px] text-ash">
        Nenhum item encontrado
      </p>
      <p className="text-[15px] text-silver">
        {theme
          ? "Tente remover o filtro de tema ou volte em breve."
          : "Nenhum item disponivel no momento. Volte em breve."}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filter bar fallback (static placeholder while Suspense resolves)
// ---------------------------------------------------------------------------

function FilterBarFallback() {
  return (
    <div className="flex gap-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-8 w-20 animate-pulse rounded-lg bg-sinal-graphite" />
      ))}
    </div>
  );
}

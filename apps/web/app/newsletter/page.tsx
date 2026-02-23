import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import FeaturedCard from "@/components/newsletter/FeaturedCard";
import ArchiveCard from "@/components/newsletter/ArchiveCard";
import FilterPills from "@/components/newsletter/FilterPills";
import SearchBar from "@/components/newsletter/SearchBar";
import Pagination from "@/components/newsletter/Pagination";
import { fetchNewsletters } from "@/lib/api";
import { mapApiToNewsletter, FALLBACK_NEWSLETTERS } from "@/lib/newsletter";

export const metadata: Metadata = {
  title: "Arquivo",
  description:
    "Todas as edições do Briefing Sinal — inteligência tech LATAM com fontes e scores de confiança.",
  openGraph: {
    title: "Arquivo | Sinal",
    description:
      "Todas as edições do Briefing Sinal — inteligência tech LATAM com fontes e scores de confiança.",
    type: "website",
  },
};

const PAGE_SIZE = 7;

export default async function NewsletterArchivePage({
  searchParams,
}: {
  searchParams: { agent?: string; q?: string; page?: string };
}) {
  const page = parseInt(searchParams.page ?? "1", 10);
  const offset = (page - 1) * PAGE_SIZE;

  const data = await fetchNewsletters({
    agent_name: searchParams.agent,
    search: searchParams.q,
    limit: PAGE_SIZE,
    offset,
  });

  const newsletters =
    data.items.length > 0
      ? data.items.map((item, i) => mapApiToNewsletter(item, i + offset))
      : FALLBACK_NEWSLETTERS;

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  // Promote the first RADAR in this page as hero (richest content).
  // If no RADAR exists in the current page, fall back to the first item.
  const radarIdx = newsletters.findIndex((n) => n.agent === "radar");
  const featuredIdx = radarIdx >= 0 ? radarIdx : 0;
  const featured = newsletters[featuredIdx];
  const rest = newsletters.filter((_, i) => i !== featuredIdx);

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-[1120px] px-[clamp(20px,4vw,48px)] py-10">
          {/* Page header */}
          <div className="mb-10 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="font-display text-[clamp(28px,4vw,40px)] text-sinal-white">Arquivo</h1>
              <p className="mt-1 text-[15px] text-ash">
                Todas as edições do Briefing Sinal, com fontes e scores de confiança.
              </p>
            </div>
            <SearchBar />
          </div>

          {/* Filter pills */}
          <div className="mb-8">
            <FilterPills />
          </div>

          {/* Cards grid */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {/* Featured card spans full width */}
            <FeaturedCard newsletter={featured} />

            {/* Remaining cards */}
            {rest.map((newsletter) => (
              <ArchiveCard key={newsletter.slug} newsletter={newsletter} />
            ))}
          </div>

          {/* Pagination */}
          <Pagination currentPage={page} totalPages={totalPages} />
        </div>
      </main>
      <Footer />
    </>
  );
}

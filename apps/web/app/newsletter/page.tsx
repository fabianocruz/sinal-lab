import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import FeaturedCard from "@/components/newsletter/FeaturedCard";
import ArchiveCard from "@/components/newsletter/ArchiveCard";
import FilterPills from "@/components/newsletter/FilterPills";
import SearchBar from "@/components/newsletter/SearchBar";
import Pagination from "@/components/newsletter/Pagination";
import { MOCK_NEWSLETTERS } from "@/lib/newsletter";

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

export default function NewsletterArchivePage() {
  const [featured, ...rest] = MOCK_NEWSLETTERS;

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
          <Pagination currentPage={1} totalPages={5} />
        </div>
      </main>
      <Footer />
    </>
  );
}

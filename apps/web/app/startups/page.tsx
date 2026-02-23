import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import CompanyCard from "@/components/startup/CompanyCard";
import SectorFilter from "@/components/startup/SectorFilter";
import SearchBar from "@/components/newsletter/SearchBar";
import Pagination from "@/components/newsletter/Pagination";
import { fetchCompanies } from "@/lib/api";

export const metadata: Metadata = {
  title: "Mapa de Startups LATAM",
  description:
    "Diretorio aberto de startups de tecnologia na America Latina — dados verificados por agentes de IA.",
  openGraph: {
    title: "Mapa de Startups LATAM | Sinal",
    description:
      "Diretorio aberto de startups de tecnologia na America Latina — dados verificados por agentes de IA.",
    type: "website",
  },
};

const PAGE_SIZE = 12;

export default async function StartupsPage({
  searchParams,
}: {
  searchParams: { sector?: string; city?: string; q?: string; page?: string };
}) {
  const page = parseInt(searchParams.page ?? "1", 10);
  const offset = (page - 1) * PAGE_SIZE;

  const data = await fetchCompanies({
    sector: searchParams.sector,
    city: searchParams.city,
    search: searchParams.q,
    limit: PAGE_SIZE,
    offset,
  });

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-[1120px] px-[clamp(20px,4vw,48px)] py-10">
          {/* Page header */}
          <div className="mb-10 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="font-display text-[clamp(28px,4vw,40px)] text-sinal-white">
                Mapa de Startups
              </h1>
              <p className="mt-1 text-[15px] text-ash">
                Startups de tecnologia na America Latina, rastreadas por agentes de IA.
              </p>
            </div>
            <SearchBar placeholder="Buscar startups..." basePath="/startups" />
          </div>

          {/* Sector filter pills */}
          <div className="mb-8">
            <SectorFilter />
          </div>

          {/* Cards grid */}
          {data.items.length > 0 ? (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((company) => (
                <CompanyCard key={company.slug} company={company} />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-6 py-16 text-center">
              <p className="font-mono text-[14px] text-ash">
                Nenhuma startup encontrada com esses filtros.
              </p>
            </div>
          )}

          {/* Pagination */}
          <Pagination currentPage={page} totalPages={totalPages} basePath="/startups" />
        </div>
      </main>
      <Footer />
    </>
  );
}

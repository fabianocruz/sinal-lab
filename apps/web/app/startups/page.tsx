import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import CompanyCard from "@/components/startup/CompanyCard";
import SectorFilter from "@/components/startup/SectorFilter";
import CountryFilter from "@/components/startup/CountryFilter";
import SearchBar from "@/components/newsletter/SearchBar";
import Pagination from "@/components/newsletter/Pagination";
import { fetchCompanies } from "@/lib/api";

export const metadata: Metadata = {
  title: "Mapa de Startups LATAM | Sinal",
  description:
    "Diret\u00f3rio aberto de startups de tecnologia na Am\u00e9rica Latina \u2014 dados verificados por agentes de IA.",
  openGraph: {
    title: "Mapa de Startups LATAM | Sinal",
    description:
      "Diret\u00f3rio aberto de startups de tecnologia na Am\u00e9rica Latina \u2014 dados verificados por agentes de IA.",
    type: "website",
  },
};

const PAGE_SIZE = 12;

export default async function StartupsPage({
  searchParams,
}: {
  searchParams: {
    sector?: string;
    city?: string;
    country?: string;
    q?: string;
    page?: string;
  };
}) {
  const page = parseInt(searchParams.page ?? "1", 10);
  const offset = (page - 1) * PAGE_SIZE;

  const data = await fetchCompanies({
    sector: searchParams.sector,
    city: searchParams.city,
    country: searchParams.country,
    search: searchParams.q,
    limit: PAGE_SIZE,
    offset,
  });

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        {/* Hero section */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pt-12">
          <div className="mb-2 flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="mb-2.5 block font-mono text-[10px] uppercase tracking-[2px] text-signal">
                Ecossistema
              </span>
              <h1 className="mb-2 font-display text-[clamp(28px,4vw,36px)] leading-[1.2] text-sinal-white">
                Mapa de Startups
              </h1>
              <p className="max-w-[520px] text-[15px] leading-[1.5] text-ash">
                Startups de tecnologia na Am&eacute;rica Latina, rastreadas por agentes de IA. Dados
                atualizados semanalmente via{" "}
                <span className="font-mono text-[12px] text-agent-mercado">INDEX</span>,{" "}
                <span className="font-mono text-[12px] text-agent-mercado">MERCADO</span> e{" "}
                <span className="font-mono text-[12px] text-agent-funding">FUNDING</span>.
              </p>
            </div>

            {/* Stats box */}
            <div className="flex gap-6 rounded-xl border border-sinal-slate bg-sinal-graphite px-6 py-4">
              <div className="text-center">
                <div className="font-display text-[28px] leading-none text-signal">
                  {data.total}
                </div>
                <div className="mt-1 font-mono text-[9px] uppercase tracking-[1px] text-[#4A4A56]">
                  Startups
                </div>
              </div>
              <div className="w-px bg-sinal-slate" />
              <div className="text-center">
                <div className="font-display text-[28px] leading-none text-sinal-white">6</div>
                <div className="mt-1 font-mono text-[9px] uppercase tracking-[1px] text-[#4A4A56]">
                  Pa&iacute;ses
                </div>
              </div>
              <div className="w-px bg-sinal-slate" />
              <div className="text-center">
                <div className="font-display text-[28px] leading-none text-sinal-white">10</div>
                <div className="mt-1 font-mono text-[9px] uppercase tracking-[1px] text-[#4A4A56]">
                  Setores
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Filters section */}
        <div className="mx-auto max-w-[1280px] border-b border-sinal-slate px-[clamp(20px,4vw,32px)] py-6">
          {/* Search + Country filter row */}
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="min-w-[240px] max-w-[400px] flex-1">
              <SearchBar placeholder="Buscar startups, setores, cidades..." basePath="/startups" />
            </div>
            <CountryFilter />
          </div>

          {/* Sector pills */}
          <SectorFilter />
        </div>

        {/* Results */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pb-12 pt-6">
          {/* Results count */}
          <div className="mb-5 flex items-center justify-between">
            <span className="font-mono text-[12px] tracking-[0.5px] text-[#4A4A56]">
              {data.total} resultado{data.total !== 1 ? "s" : ""}
              {searchParams.sector && ` em ${searchParams.sector}`}
            </span>
          </div>

          {/* Cards grid */}
          {data.items.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((company) => (
                <CompanyCard key={company.slug} company={company} />
              ))}
            </div>
          ) : (
            <div className="py-20 text-center">
              <p className="mb-2 text-[16px] text-ash">Nenhuma startup encontrada</p>
              <p className="text-[13px] text-[#4A4A56]">
                Tente ajustar os filtros ou buscar por outro termo.
              </p>
            </div>
          )}

          {/* Pagination */}
          <Pagination currentPage={page} totalPages={totalPages} basePath="/startups" />
        </div>

        {/* Methodology badge */}
        <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] pb-12">
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-sinal-slate bg-sinal-graphite px-6 py-5">
            <div className="flex items-center gap-4">
              <div className="h-2 w-2 animate-pulse rounded-full bg-agent-radar" />
              <div>
                <p className="mb-0.5 text-[13px] text-silver">
                  Dados coletados por agentes{" "}
                  <span className="font-mono text-[11px] text-agent-mercado">INDEX</span>,{" "}
                  <span className="font-mono text-[11px] text-agent-mercado">MERCADO</span> e{" "}
                  <span className="font-mono text-[11px] text-agent-funding">FUNDING</span>
                </p>
                <p className="font-mono text-[11px] text-[#4A4A56]">
                  Fontes: GitHub, LinkedIn, ABStartups, CoreSignal, YC
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

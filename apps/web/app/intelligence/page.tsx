import type { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Pagination from "@/components/newsletter/Pagination";
import { fetchIntelligenceReports } from "@/lib/api";
import { CARD_GRADIENTS } from "@/lib/newsletter";
import type { ContentApiItem } from "@/lib/newsletter";

export const metadata: Metadata = {
  title: "Intelligence",
  description: "Relatorios de inteligencia de mercado sobre o ecossistema tech da America Latina.",
  openGraph: {
    title: "Intelligence | Sinal",
    description:
      "Relatorios de inteligencia de mercado sobre o ecossistema tech da America Latina.",
    type: "website",
  },
};

const PAGE_SIZE = 9;
const ACCENT = "#59B4FF";
const ACCENT_BG = "rgba(89,180,255,0.15)";

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function FeaturedReportCard({ item }: { item: ContentApiItem }) {
  const dateStr = formatDate(item.published_at);

  return (
    <Link
      href={`/intelligence/${item.slug}`}
      className="group col-span-full grid overflow-hidden rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite transition-colors duration-300 hover:border-[rgba(255,255,255,0.10)] md:grid-cols-[1.2fr_1fr]"
      aria-label={`Ler: ${item.title}`}
    >
      {/* Image */}
      <div
        className="relative min-h-[220px] overflow-hidden md:min-h-[320px]"
        style={{ background: CARD_GRADIENTS[1] }}
        aria-hidden="true"
      >
        {item.metadata_?.hero_image?.url && (
          <img
            src={item.metadata_.hero_image.url}
            alt=""
            className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
          />
        )}
        {/* Badge */}
        <div
          className="absolute left-3 top-3 flex items-center gap-[5px] rounded-[5px] bg-[rgba(10,10,11,0.75)] px-[10px] py-[5px] font-mono text-[9px] font-semibold uppercase tracking-[1.5px] backdrop-blur-[8px]"
          style={{ color: ACCENT }}
        >
          <span
            className="inline-block h-[5px] w-[5px] rounded-full"
            style={{ backgroundColor: ACCENT }}
          />
          Intelligence
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-col justify-center px-7 py-8 md:px-[28px] md:py-8">
        {/* Meta row */}
        <div className="mb-3 flex items-center">
          <span className="font-mono text-[12px] tracking-[0.5px] text-ash">{dateStr}</span>
        </div>

        {/* Title */}
        <h2 className="mb-3 font-display text-[24px] leading-[1.3] text-sinal-white">
          {item.title}
        </h2>

        {/* Subtitle */}
        <p className="mb-5 text-[15px] leading-[1.5] text-ash">
          {item.subtitle ?? item.summary ?? item.meta_description ?? ""}
        </p>

        {/* Author footer */}
        <div className="flex items-center gap-[10px]">
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-[10px] font-semibold"
            style={{ backgroundColor: ACCENT_BG, color: ACCENT }}
            aria-hidden="true"
          >
            {(item.author_name ?? "Sinal Intelligence").charAt(0)}&middot;
          </div>
          <div className="text-[13px]">
            <strong className="block text-bone">{item.author_name ?? "Sinal Intelligence"}</strong>
            <span className="text-[12px] text-ash">Market Intelligence</span>
          </div>
        </div>
      </div>
    </Link>
  );
}

function ReportCard({ item, index }: { item: ContentApiItem; index: number }) {
  const dateStr = formatDate(item.published_at);
  const gradientIndex = ((index % 6) + 1) as 1 | 2 | 3 | 4 | 5 | 6;

  return (
    <Link
      href={`/intelligence/${item.slug}`}
      className="group block overflow-hidden rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite transition-all duration-300 hover:-translate-y-[3px] hover:border-[rgba(255,255,255,0.10)]"
      aria-label={`Ler: ${item.title}`}
    >
      {/* Cover image area */}
      <div
        className="relative aspect-[16/10] overflow-hidden"
        style={{ background: CARD_GRADIENTS[gradientIndex] }}
        aria-hidden="true"
      >
        {item.metadata_?.hero_image?.url && (
          <img
            src={item.metadata_.hero_image.url}
            alt=""
            className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
          />
        )}
        {/* Type badge */}
        <div
          className="absolute left-3 top-3 flex items-center gap-[5px] rounded-[5px] bg-[rgba(10,10,11,0.75)] px-[10px] py-[5px] font-mono text-[9px] font-semibold uppercase tracking-[1.5px] backdrop-blur-[8px]"
          style={{ color: ACCENT }}
        >
          <span
            className="inline-block h-[5px] w-[5px] rounded-full"
            style={{ backgroundColor: ACCENT }}
            aria-hidden="true"
          />
          Intelligence
        </div>
      </div>

      {/* Body */}
      <div className="px-[22px] pb-6 pt-5">
        <div className="mb-3">
          <span className="font-mono text-[12px] tracking-[0.5px] text-ash">{dateStr}</span>
        </div>

        <h2 className="mb-2 font-display text-[18px] leading-[1.35] text-sinal-white">
          {item.title}
        </h2>

        <p className="mb-4 text-[14px] leading-[1.5] text-ash">
          {item.subtitle ?? item.summary ?? item.meta_description ?? ""}
        </p>

        <div className="flex items-center gap-[10px]">
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-[10px] font-semibold"
            style={{ backgroundColor: ACCENT_BG, color: ACCENT }}
            aria-hidden="true"
          >
            {(item.author_name ?? "Sinal Intelligence").charAt(0)}&middot;
          </div>
          <div className="text-[13px]">
            <strong className="block text-bone">{item.author_name ?? "Sinal Intelligence"}</strong>
            <span className="text-[12px] text-ash">Market Intelligence</span>
          </div>
        </div>
      </div>
    </Link>
  );
}

export default async function IntelligencePage({
  searchParams,
}: {
  searchParams: { page?: string };
}) {
  const page = parseInt(searchParams.page ?? "1", 10);
  const offset = (page - 1) * PAGE_SIZE;

  const data = await fetchIntelligenceReports({ limit: PAGE_SIZE, offset });

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  const featured = data.items[0] ?? null;
  const rest = data.items.slice(1);

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-[1120px] px-[clamp(20px,4vw,48px)] py-10">
          {/* Page header */}
          <div className="mb-10">
            <h1 className="font-display text-[clamp(28px,4vw,40px)] text-sinal-white">
              Intelligence
            </h1>
            <p className="mt-1 text-[15px] text-ash">
              Relatorios de inteligencia de mercado com dados exclusivos sobre o ecossistema tech
              LATAM.
            </p>
          </div>

          {/* Reports */}
          {!featured ? (
            <p className="py-16 text-center font-mono text-[14px] text-ash">
              Nenhum relatorio publicado ainda.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {/* Featured report — full width */}
              <FeaturedReportCard item={featured} />

              {/* Remaining reports */}
              {rest.map((item, index) => (
                <ReportCard key={item.id} item={item} index={index + 1} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {data.items.length > 0 && (
            <Pagination currentPage={page} totalPages={totalPages} basePath="/intelligence" />
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}

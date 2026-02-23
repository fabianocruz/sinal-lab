import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import CompanyDetail from "@/components/startup/CompanyDetail";
import { fetchCompanyBySlug } from "@/lib/api";
import { companyJsonLd } from "@/lib/jsonld";

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const company = await fetchCompanyBySlug(params.slug);

  if (!company) return { title: "Startup nao encontrada" };

  const description =
    company.short_description ??
    company.description?.slice(0, 160) ??
    `${company.name} — startup de tecnologia em ${company.country}`;

  return {
    title: company.name,
    description,
    openGraph: {
      title: `${company.name} | Sinal`,
      description,
      type: "profile",
    },
  };
}

export default async function StartupSlugPage({ params }: PageProps) {
  const company = await fetchCompanyBySlug(params.slug);

  if (!company) {
    notFound();
  }

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <CompanyDetail company={company} />
      </main>
      <Footer />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(companyJsonLd(company)) }}
      />
    </>
  );
}

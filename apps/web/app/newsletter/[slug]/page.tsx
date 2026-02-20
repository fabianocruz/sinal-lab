import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import NewsletterContent from "@/components/newsletter/NewsletterContent";
import { MOCK_NEWSLETTERS } from "@/lib/newsletter";

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const newsletter = MOCK_NEWSLETTERS.find((n) => n.slug === params.slug);

  if (!newsletter) {
    return { title: "Edicao nao encontrada" };
  }

  return {
    title: newsletter.title,
    description: newsletter.subtitle,
    openGraph: {
      title: newsletter.title,
      description: newsletter.subtitle,
      type: "article",
      publishedTime: newsletter.dateISO,
    },
  };
}

export async function generateStaticParams() {
  return MOCK_NEWSLETTERS.map((n) => ({ slug: n.slug }));
}

export default function NewsletterSlugPage({ params }: PageProps) {
  const newsletter = MOCK_NEWSLETTERS.find((n) => n.slug === params.slug);

  if (!newsletter) {
    notFound();
  }

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <NewsletterContent newsletter={newsletter} />
      </main>
      <Footer />
    </>
  );
}

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import NewsletterContent from "@/components/newsletter/NewsletterContent";
import { fetchNewsletterBySlug } from "@/lib/api";
import { mapApiToNewsletter, FALLBACK_NEWSLETTERS } from "@/lib/newsletter";

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const apiItem = await fetchNewsletterBySlug(params.slug);

  if (apiItem) {
    return {
      title: apiItem.title,
      description: apiItem.subtitle ?? apiItem.summary ?? apiItem.meta_description,
      openGraph: {
        title: apiItem.title,
        description: apiItem.subtitle ?? apiItem.summary ?? "",
        type: "article",
        publishedTime: apiItem.published_at ?? undefined,
      },
    };
  }

  const fallback = FALLBACK_NEWSLETTERS.find((n) => n.slug === params.slug);
  if (!fallback) return { title: "Edição não encontrada" };
  return { title: fallback.title, description: fallback.subtitle };
}

export default async function NewsletterSlugPage({ params }: PageProps) {
  const apiItem = await fetchNewsletterBySlug(params.slug);

  let newsletter;
  if (apiItem) {
    newsletter = mapApiToNewsletter(apiItem, 0);
  } else {
    newsletter = FALLBACK_NEWSLETTERS.find((n) => n.slug === params.slug);
  }

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

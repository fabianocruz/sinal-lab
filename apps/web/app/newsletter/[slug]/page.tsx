import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import NewsletterContent from "@/components/newsletter/NewsletterContent";
import { fetchNewsletterBySlug } from "@/lib/api";
import {
  mapApiToNewsletter,
  FALLBACK_NEWSLETTERS,
  type NewsletterMetadata,
} from "@/lib/newsletter";
import { articleJsonLd } from "@/lib/jsonld";

export const revalidate = 300;

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const apiItem = await fetchNewsletterBySlug(params.slug);

  if (apiItem) {
    const meta = apiItem.metadata_ as NewsletterMetadata | undefined;
    const ogImage = meta?.hero_image?.url;

    return {
      title: apiItem.title,
      description: apiItem.subtitle ?? apiItem.summary ?? apiItem.meta_description,
      openGraph: {
        title: apiItem.title,
        description: apiItem.subtitle ?? apiItem.summary ?? "",
        type: "article",
        publishedTime: apiItem.published_at ?? undefined,
        ...(ogImage && { images: [{ url: ogImage, alt: meta?.hero_image?.alt }] }),
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

  const jsonLd = apiItem
    ? articleJsonLd(
        apiItem.title,
        apiItem.subtitle ?? apiItem.summary ?? "",
        apiItem.published_at,
        apiItem.slug,
      )
    : null;

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <NewsletterContent newsletter={newsletter} />
      </main>
      <Footer />
      {jsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
    </>
  );
}

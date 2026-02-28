import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import ArticleContent from "@/components/article/ArticleContent";
import { fetchNewsletterBySlug } from "@/lib/api";

export const revalidate = 300;

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const item = await fetchNewsletterBySlug(params.slug);
  if (!item) return { title: "Artigo nao encontrado" };

  return {
    title: item.title,
    description: item.subtitle ?? item.summary ?? item.meta_description ?? "",
    openGraph: {
      title: item.title,
      description: item.subtitle ?? item.summary ?? "",
      type: "article",
      publishedTime: item.published_at ?? undefined,
    },
  };
}

export default async function ArticleSlugPage({ params }: PageProps) {
  const item = await fetchNewsletterBySlug(params.slug);
  if (!item) notFound();

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <ArticleContent item={item} />
      </main>
      <Footer />
    </>
  );
}

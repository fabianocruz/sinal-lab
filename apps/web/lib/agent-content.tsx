import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import NewsletterContent from "@/components/newsletter/NewsletterContent";
import { fetchNewsletterBySlug } from "@/lib/api";
import { mapApiToNewsletter } from "@/lib/newsletter";
import { AGENT_PERSONAS, type AgentKey } from "@/lib/constants";

export async function generateAgentContentMetadata(
  agentName: AgentKey,
  slug: string,
): Promise<Metadata> {
  const apiItem = await fetchNewsletterBySlug(slug);
  const agentCode = AGENT_PERSONAS[agentName].agentCode;

  if (!apiItem) {
    return { title: "Conteúdo não encontrado" };
  }

  const description = apiItem.subtitle ?? apiItem.summary ?? apiItem.meta_description ?? undefined;

  return {
    title: `${apiItem.title} | ${agentCode} | Sinal`,
    description,
    openGraph: {
      title: `${apiItem.title} | ${agentCode} | Sinal`,
      description: apiItem.subtitle ?? apiItem.summary ?? "",
      type: "article",
      publishedTime: apiItem.published_at ?? undefined,
    },
  };
}

export default async function AgentContentPage({
  agentName,
  slug,
}: {
  agentName: AgentKey;
  slug: string;
}) {
  const apiItem = await fetchNewsletterBySlug(slug);

  if (!apiItem) {
    notFound();
  }

  const newsletter = mapApiToNewsletter(apiItem, 0);

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

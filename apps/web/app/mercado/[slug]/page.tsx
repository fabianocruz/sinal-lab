import type { Metadata } from "next";
import AgentContentPage, { generateAgentContentMetadata } from "@/lib/agent-content";

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  return generateAgentContentMetadata("mercado", params.slug);
}

export default async function MercadoSlugPage({ params }: PageProps) {
  return <AgentContentPage agentName="mercado" slug={params.slug} />;
}

import type { Metadata } from "next";
import AgentContentPage, { generateAgentContentMetadata } from "@/lib/agent-content";

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  return generateAgentContentMetadata("codigo", params.slug);
}

export default async function CodigoSlugPage({ params }: PageProps) {
  return <AgentContentPage agentName="codigo" slug={params.slug} />;
}

import type { Metadata } from "next";
import AgentContentPage, { generateAgentContentMetadata } from "@/lib/agent-content";

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  return generateAgentContentMetadata("radar", params.slug);
}

export default async function RadarSlugPage({ params }: PageProps) {
  return <AgentContentPage agentName="radar" slug={params.slug} />;
}

import type { Metadata } from "next";
import AgentContentPage, { generateAgentContentMetadata } from "@/lib/agent-content";

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  return generateAgentContentMetadata("funding", params.slug);
}

export default async function FundingSlugPage({ params }: PageProps) {
  return <AgentContentPage agentName="funding" slug={params.slug} />;
}

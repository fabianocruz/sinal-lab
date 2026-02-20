import { AGENT_PERSONAS, AgentKey } from "@/lib/constants";
import Section from "@/components/layout/Section";
import AgentCard from "./AgentCard";

const AGENT_KEYS = Object.keys(AGENT_PERSONAS) as AgentKey[];

/**
 * Full-width section that introduces all five agent personas.
 * Uses the shared Section wrapper for consistent layout and the EQUIPE label.
 */
export default function AgentTeam() {
  return (
    <Section label="EQUIPE" id="equipe">
      {/* Headings */}
      <h2 className="mb-4 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
        Nosso time de agentes.
      </h2>
      <p className="mb-12 max-w-[640px] text-[17px] leading-[1.7] text-silver">
        Cinco personalidades especializadas. Centenas de agentes executores. Uma inteligência
        coletiva.
      </p>

      {/* Agent grid — 1 col mobile, 2 col tablet, 3 col desktop */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {AGENT_KEYS.map((key) => (
          <AgentCard key={key} agentKey={key} />
        ))}
      </div>
    </Section>
  );
}

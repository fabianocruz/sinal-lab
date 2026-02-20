import { AGENT_PERSONAS, AgentKey } from "@/lib/constants";
import AgentAvatar from "./AgentAvatar";

export interface AgentCardProps {
  agentKey: AgentKey;
}

/** Badge background colors at 10% opacity, keyed by agent. */
const BADGE_BG: Record<AgentKey, string> = {
  sintese: "rgba(232,255,89,0.10)",
  radar: "rgba(89,255,180,0.10)",
  codigo: "rgba(89,180,255,0.10)",
  funding: "rgba(255,138,89,0.10)",
  mercado: "rgba(196,89,255,0.10)",
};

/**
 * Card displaying a single agent persona with avatar, name, role, agent code
 * badge, and description. Purely presentational server component.
 */
export default function AgentCard({ agentKey }: AgentCardProps) {
  const persona = AGENT_PERSONAS[agentKey];

  return (
    <article
      aria-label={`Agente ${persona.name}`}
      className="relative rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-6 transition-transform duration-200 hover:-translate-y-0.5"
    >
      {/* Status dot — top-right corner */}
      <span
        aria-hidden="true"
        className="absolute right-5 top-5 block h-[5px] w-[5px] rounded-full"
        style={{ backgroundColor: persona.color }}
      />

      {/* Avatar + identity row */}
      <div className="flex items-start gap-4">
        <AgentAvatar agentKey={agentKey} size="lg" />

        <div className="min-w-0">
          {/* Name */}
          <p className="font-body text-[16px] font-semibold leading-snug text-sinal-white">
            {persona.name}
          </p>

          {/* Role */}
          <p className="mt-0.5 font-mono text-[12px] text-ash">{persona.role}</p>

          {/* Agent code badge */}
          <span
            aria-label={`Codigo do agente: ${persona.agentCode}`}
            className="mt-2 inline-block rounded-full px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider"
            style={{
              backgroundColor: BADGE_BG[agentKey],
              color: persona.color,
            }}
          >
            {persona.agentCode}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="mt-4 text-[14px] leading-relaxed text-silver">{persona.description}</p>
    </article>
  );
}

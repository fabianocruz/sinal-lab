import Link from "next/link";
import { AGENT_PERSONAS } from "@/lib/constants";
import { Newsletter, CARD_GRADIENTS, AGENT_HEX } from "@/lib/newsletter";

interface ArchiveCardProps {
  newsletter: Newsletter;
}

export default function ArchiveCard({ newsletter }: ArchiveCardProps) {
  const persona = AGENT_PERSONAS[newsletter.agent];
  const agentInitial = newsletter.agentLabel.charAt(0);

  return (
    <Link
      href={`/newsletter/${newsletter.slug}`}
      className="group block overflow-hidden rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite transition-all duration-300 hover:-translate-y-[3px] hover:border-[rgba(255,255,255,0.10)]"
      aria-label={`Ler: ${newsletter.title}`}
    >
      {/* Image area */}
      <div
        className="relative aspect-[16/10]"
        style={{ background: CARD_GRADIENTS[newsletter.gradientIndex] }}
        aria-hidden="true"
      >
        {/* Agent badge */}
        <div
          className="absolute left-3 top-3 flex items-center gap-[5px] rounded-[5px] bg-[rgba(10,10,11,0.75)] px-[10px] py-[5px] font-mono text-[9px] font-semibold uppercase tracking-[1.5px] backdrop-blur-[8px]"
          style={{ color: AGENT_HEX[newsletter.agent] }}
        >
          <span
            className="inline-block h-[5px] w-[5px] rounded-full"
            style={{ backgroundColor: AGENT_HEX[newsletter.agent] }}
          />
          {newsletter.agentLabel}
        </div>

        {/* DQ badge */}
        {newsletter.dqScore && (
          <div className="absolute right-3 top-3 rounded-[5px] bg-[rgba(10,10,11,0.75)] px-2 py-[5px] font-mono text-[9px] tracking-[0.5px] text-signal backdrop-blur-[8px]">
            DQ: {newsletter.dqScore}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="px-[22px] pb-6 pt-5">
        {/* Meta row */}
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-[12px] tracking-[0.5px] text-ash">{newsletter.date}</span>
          <span className="flex items-center gap-1 font-mono text-[12px] text-ash">
            <HeartIcon />
            {newsletter.likes}
          </span>
        </div>

        {/* Title */}
        <h2 className="mb-2 font-display text-[18px] leading-[1.35] text-sinal-white">
          {newsletter.title}
        </h2>

        {/* Subtitle */}
        <p className="mb-4 text-[14px] leading-[1.5] text-ash">{newsletter.subtitle}</p>

        {/* Footer */}
        <div className="flex items-center gap-[10px]">
          <AgentAvatar agent={newsletter.agent} initial={agentInitial} />
          <div className="text-[13px]">
            <strong className="block text-bone">{persona.name}</strong>
            <span className="text-[12px] text-ash">{persona.role}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}

/** Inline heart SVG matching branding HTML exactly. */
function HeartIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-[14px] w-[14px]"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  );
}

interface AgentAvatarProps {
  agent: keyof typeof AGENT_PERSONAS;
  initial: string;
}

/** Colored circular avatar with agent initial — matches branding CSS. */
function AgentAvatar({ agent, initial }: AgentAvatarProps) {
  const bgAlpha: Record<string, string> = {
    sintese: "rgba(232,255,89,0.15)",
    radar: "rgba(89,255,180,0.15)",
    codigo: "rgba(89,180,255,0.15)",
    funding: "rgba(255,138,89,0.15)",
    mercado: "rgba(196,89,255,0.15)",
  };

  return (
    <div
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-[10px] font-semibold"
      style={{
        backgroundColor: bgAlpha[agent] ?? "rgba(255,255,255,0.1)",
        color: AGENT_HEX[agent],
      }}
      aria-hidden="true"
    >
      {initial}&middot;
    </div>
  );
}

import Link from "next/link";
import { AGENT_PERSONAS } from "@/lib/constants";
import { Newsletter, CARD_GRADIENTS, AGENT_HEX } from "@/lib/newsletter";

interface FeaturedCardProps {
  newsletter: Newsletter;
}

export default function FeaturedCard({ newsletter }: FeaturedCardProps) {
  const persona = AGENT_PERSONAS[newsletter.agent];
  const agentInitial = newsletter.agentLabel.charAt(0);

  const bgAlpha: Record<string, string> = {
    sintese: "rgba(232,255,89,0.15)",
    radar: "rgba(89,255,180,0.15)",
    codigo: "rgba(89,180,255,0.15)",
    funding: "rgba(255,138,89,0.15)",
    mercado: "rgba(196,89,255,0.15)",
  };

  return (
    <Link
      href={`/newsletter/${newsletter.slug}`}
      className="group col-span-full grid overflow-hidden rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite transition-colors duration-300 hover:border-[rgba(255,255,255,0.10)] md:grid-cols-[1.2fr_1fr]"
      aria-label={`Ler edição em destaque: ${newsletter.title}`}
    >
      {/* Image */}
      <div
        className="relative min-h-[220px] overflow-hidden md:min-h-[320px]"
        style={{ background: CARD_GRADIENTS[newsletter.gradientIndex] }}
        aria-hidden="true"
      >
        {newsletter.metadata?.hero_image?.url && (
          <img
            src={newsletter.metadata.hero_image.url}
            alt=""
            className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
          />
        )}
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
      <div className="flex flex-col justify-center px-7 py-8 md:px-[28px] md:py-8">
        {/* Meta row */}
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-[12px] tracking-[0.5px] text-ash">
            {newsletter.date} &middot; Ed. #{newsletter.edition}
          </span>
          <span className="flex items-center gap-1 font-mono text-[12px] text-ash">
            <HeartIcon />
            {newsletter.likes}
          </span>
        </div>

        {/* Title */}
        <h2 className="mb-3 font-display text-[24px] leading-[1.3] text-sinal-white">
          {newsletter.title}
        </h2>

        {/* Subtitle */}
        <p className="mb-5 text-[15px] leading-[1.5] text-ash">{newsletter.subtitle}</p>

        {/* Agent footer */}
        <div className="flex items-center gap-[10px]">
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-[10px] font-semibold"
            style={{
              backgroundColor: bgAlpha[newsletter.agent] ?? "rgba(255,255,255,0.1)",
              color: AGENT_HEX[newsletter.agent],
            }}
            aria-hidden="true"
          >
            {agentInitial}&middot;
          </div>
          <div className="text-[13px]">
            <strong className="block text-bone">{persona.name}</strong>
            <span className="text-[12px] text-ash">{persona.role}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}

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

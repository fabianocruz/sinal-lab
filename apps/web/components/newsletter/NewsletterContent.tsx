"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { Newsletter, AGENT_HEX } from "@/lib/newsletter";
import { AGENT_PERSONAS } from "@/lib/constants";
import GatedOverlay from "@/components/newsletter/GatedOverlay";

interface NewsletterContentProps {
  newsletter: Newsletter;
}

const AGENT_BG_ALPHA: Record<string, string> = {
  sintese: "rgba(232,255,89,0.15)",
  radar: "rgba(89,255,180,0.15)",
  codigo: "rgba(89,180,255,0.15)",
  funding: "rgba(255,138,89,0.15)",
  mercado: "rgba(196,89,255,0.15)",
};

export default function NewsletterContent({ newsletter }: NewsletterContentProps) {
  const { status } = useSession();
  const isAuthenticated = status === "authenticated";

  const agentColor = AGENT_HEX[newsletter.agent];
  const persona = AGENT_PERSONAS[newsletter.agent];
  const agentBgAlpha = AGENT_BG_ALPHA[newsletter.agent] ?? "rgba(255,255,255,0.1)";

  const paragraphs = newsletter.body.split("\n\n").filter((p) => p.trim().length > 0);
  const previewCount = Math.ceil(paragraphs.length * 0.3);
  const previewParagraphs = paragraphs.slice(0, previewCount);
  const remainingParagraphs = paragraphs.slice(previewCount);

  return (
    <article className="mx-auto max-w-[720px] px-6 py-12 md:px-10">
      {/* Back link */}
      <Link
        href="/newsletter"
        className="mb-8 inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
      >
        &larr; Voltar ao Arquivo
      </Link>

      {/* Article header */}
      <header className="mb-10 border-b border-[rgba(255,255,255,0.06)] pb-10">
        {/* Edition label */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          {/* Agent dot + name */}
          <div
            className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[1.5px]"
            style={{ color: agentColor }}
          >
            <span
              className="inline-block h-[5px] w-[5px] rounded-full"
              style={{ backgroundColor: agentColor }}
              aria-hidden="true"
            />
            {newsletter.agentLabel}
          </div>

          <span className="text-[rgba(255,255,255,0.12)]">/</span>

          {/* Edition + date */}
          <span className="font-mono text-[11px] tracking-[0.5px] text-ash">
            Edição #{newsletter.edition} &middot; {newsletter.date}
          </span>

          {/* DQ badge */}
          {newsletter.dqScore && (
            <span className="rounded-[5px] bg-[rgba(232,255,89,0.06)] px-2 py-1 font-mono text-[10px] text-signal">
              DQ: {newsletter.dqScore}
            </span>
          )}
        </div>

        {/* Title */}
        <h1 className="font-display text-[clamp(24px,4vw,36px)] leading-[1.2] text-sinal-white">
          {newsletter.title}
        </h1>

        {/* Subtitle */}
        <p className="mt-4 text-[16px] leading-relaxed text-silver">{newsletter.subtitle}</p>

        {/* Agent info */}
        <div className="mt-6 flex items-center gap-3">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-mono text-[11px] font-semibold"
            style={{ backgroundColor: agentBgAlpha, color: agentColor }}
            aria-hidden="true"
          >
            {newsletter.agentLabel.charAt(0)}&middot;
          </div>
          <div>
            <p className="text-[13px] font-semibold text-bone">{persona.name}</p>
            <p className="text-[12px] text-ash">{persona.role}</p>
          </div>
        </div>
      </header>

      {/* Article body — always-visible preview */}
      <div className="prose-sinal">
        {previewParagraphs.map((paragraph, index) => (
          <p key={index} className="mb-6 text-[16px] leading-[1.8] text-silver last:mb-0">
            {paragraph}
          </p>
        ))}
      </div>

      {/* Gated content or remaining paragraphs */}
      {remainingParagraphs.length > 0 && (
        <>
          {isAuthenticated ? (
            <div className="prose-sinal mt-0">
              {remainingParagraphs.map((paragraph, index) => (
                <p
                  key={`gated-${index}`}
                  className="mb-6 text-[16px] leading-[1.8] text-silver last:mb-0"
                >
                  {paragraph}
                </p>
              ))}
            </div>
          ) : (
            <GatedOverlay />
          )}
        </>
      )}

      {/* Footer note — only visible when authenticated or all content is preview */}
      {(isAuthenticated || remainingParagraphs.length === 0) && (
        <>
          <div className="mt-12 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-6">
            <p className="font-mono text-[12px] text-ash">
              <strong className="text-bone">Sinal</strong> é gerado por 5 agentes de IA e revisado
              por editores humanos.{" "}
              <Link href="/#metodologia" className="text-signal underline underline-offset-2">
                Metodologia
              </Link>{" "}
              &middot;{" "}
              <Link href="#" className="text-signal underline underline-offset-2">
                Fontes
              </Link>
            </p>
          </div>

          <div className="mt-8">
            <Link
              href="/newsletter"
              className="inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
            >
              &larr; Ver todas as edições
            </Link>
          </div>
        </>
      )}

      {/* Back link bottom — always visible for unauthenticated users */}
      {!isAuthenticated && remainingParagraphs.length > 0 && (
        <div className="mt-8">
          <Link
            href="/newsletter"
            className="inline-flex items-center gap-2 font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
          >
            &larr; Ver todas as edições
          </Link>
        </div>
      )}
    </article>
  );
}

"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";

export default function Hero() {
  const { status: authStatus } = useSession();

  return (
    <section id="hero" className="relative overflow-hidden">
      {/* Background glows */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-[20%] -top-[30%] h-[70%] w-[70%]"
        style={{
          background: "radial-gradient(ellipse, rgba(232,255,89,0.06) 0%, transparent 60%)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-[20%] -left-[10%] h-[50%] w-[50%]"
        style={{
          background: "radial-gradient(ellipse, rgba(89,255,180,0.04) 0%, transparent 60%)",
        }}
      />

      <div className="relative z-10 mx-auto max-w-container px-6 pb-16 pt-[calc(72px+3rem)] md:px-10 md:pb-20 md:pt-[calc(72px+4rem)]">
        <div className="max-w-[720px]">
          {/* Label */}
          <div className="mb-6 flex items-center gap-2.5">
            <span className="block h-px w-6 bg-signal" />
            <span className="font-mono text-[12px] font-semibold uppercase tracking-[2.5px] text-signal">
              Briefing semanal gratuito
            </span>
          </div>

          {/* Headline */}
          <h1 className="mb-7 font-display text-[clamp(40px,6vw,72px)] font-normal leading-[1.08] tracking-[-0.02em] text-sinal-white">
            O ecossistema tech LATAM,
            <br />
            toda terça no seu <em className="italic text-signal">inbox.</em>
          </h1>

          {/* Subheadline */}
          <p className="mb-8 max-w-[580px] text-[clamp(17px,2vw,19px)] leading-[1.7] text-ash">
            Dados de funding, tendências e mercado pesquisados por agentes de IA, verificados por
            humanos. Grátis.
          </p>

          {/* Social proof — above CTA for trust before action */}
          <p className="mb-8 font-mono text-[14px] text-signal">
            +2.500 fundadores, CTOs e investidores já recebem o Sinal.
          </p>

          {/* CTA */}
          {authStatus === "authenticated" ? (
            <div className="mb-12 flex items-center gap-3 rounded-xl border border-[rgba(232,255,89,0.2)] bg-[rgba(232,255,89,0.06)] px-5 py-4 max-w-[480px]">
              <span className="text-signal">✓</span>
              <p className="font-mono text-[14px] text-signal">
                Você já recebe o Briefing.{" "}
                <Link href="/newsletter" className="underline underline-offset-2 hover:opacity-80">
                  Ver últimas edições →
                </Link>
              </p>
            </div>
          ) : (
            <>
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link
                  href="/cadastro"
                  className="inline-flex items-center justify-center rounded-[10px] border border-signal bg-signal px-7 py-4 font-body text-[15px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim"
                >
                  Receber o Briefing grátis
                </Link>
                <Link
                  href="#edicoes"
                  className="inline-flex items-center justify-center rounded-[10px] border border-[rgba(255,255,255,0.12)] px-7 py-4 font-body text-[15px] font-semibold text-ash transition-colors hover:border-[rgba(255,255,255,0.25)] hover:text-sinal-white"
                >
                  Ler a última edição →
                </Link>
              </div>

              {/* Micro copy */}
              <p className="text-[13px] text-sinal-slate">
                Toda terça-feira. Sem spam. Saia quando quiser.
              </p>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

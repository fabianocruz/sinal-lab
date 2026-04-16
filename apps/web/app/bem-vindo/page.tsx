import { Suspense } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import SignupForm from "@/components/auth/SignupForm";

export const metadata: Metadata = {
  title: "Bem-vindo ao Sinal",
  description:
    "Briefing semanal com dados de funding, tendências e mercado do ecossistema tech LATAM. Pesquisado por agentes de IA, verificado por humanos. Grátis.",
};

export default function BemVindoPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-sinal-black px-6 py-16">
      {/* Logo */}
      <Link href="/" className="mb-10 flex items-center gap-1.5">
        <span className="font-display text-2xl text-sinal-white">Sinal</span>
        <span className="inline-block h-[7px] w-[7px] rounded-full bg-signal shadow-[0_0_12px_rgba(232,255,89,0.4)]" />
      </Link>

      {/* Card */}
      <div className="w-full max-w-[440px] rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-8 shadow-[0_8px_40px_rgba(0,0,0,0.4)]">
        <div className="mb-7 text-center">
          <p className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
            Briefing semanal gratuito
          </p>
          <h1 className="font-display text-[28px] leading-[1.15] text-sinal-white">
            O ecossistema tech LATAM,
            <br />
            toda terça no seu inbox.
          </h1>
          <p className="mt-3 text-[15px] leading-[1.6] text-ash">
            Dados de funding, tendências e mercado pesquisados por agentes de IA, verificados por
            humanos. Grátis.
          </p>
        </div>

        {/* Social proof */}
        <p className="mb-6 text-center font-mono text-[13px] text-signal">
          +2.500 fundadores, CTOs e investidores já recebem.
        </p>

        <Suspense>
          <SignupForm />
        </Suspense>

        <p className="mt-5 text-center text-[12px] text-sinal-slate">
          Toda terça-feira. Sem spam. Saia quando quiser.
        </p>
      </div>

      {/* Back to home */}
      <Link href="/" className="mt-8 text-[13px] text-ash transition-colors hover:text-sinal-white">
        Conhecer o Sinal →
      </Link>
    </main>
  );
}

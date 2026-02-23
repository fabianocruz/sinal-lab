"use client";

import Link from "next/link";

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function StartupsError({ reset }: ErrorProps) {
  return (
    <div className="flex min-h-screen items-center justify-center pt-[72px]">
      <div className="mx-auto max-w-[480px] px-6 text-center">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[2px] text-signal">Erro</p>
        <h1 className="mb-4 font-display text-[28px] text-sinal-white">Algo deu errado</h1>
        <p className="mb-8 text-[15px] text-ash">
          Nao foi possivel carregar o mapa de startups. Tente novamente.
        </p>
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={reset}
            className="rounded-lg bg-signal px-6 py-3 font-mono text-[13px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim"
          >
            Tentar novamente
          </button>
          <Link
            href="/"
            className="rounded-lg border border-[rgba(255,255,255,0.06)] px-6 py-3 font-mono text-[13px] text-ash transition-colors hover:text-sinal-white"
          >
            Voltar ao inicio
          </Link>
        </div>
      </div>
    </div>
  );
}

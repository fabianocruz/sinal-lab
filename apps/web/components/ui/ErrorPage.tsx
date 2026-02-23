"use client";

import Link from "next/link";

interface ErrorPageProps {
  error: Error;
  reset: () => void;
  title: string;
  message: string;
  backHref: string;
  backLabel: string;
}

export default function ErrorPage({ reset, title, message, backHref, backLabel }: ErrorPageProps) {
  return (
    <div className="flex min-h-screen items-center justify-center pt-[72px]">
      <div className="mx-auto max-w-[480px] px-6 text-center">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[2px] text-signal">{title}</p>
        <h1 className="mb-4 font-display text-[28px] text-sinal-white">Algo deu errado</h1>
        <p className="mb-8 text-[15px] text-ash">{message}</p>
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={reset}
            className="rounded-lg bg-signal px-6 py-3 font-mono text-[13px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim"
          >
            Tentar novamente
          </button>
          <Link
            href={backHref}
            className="rounded-lg border border-[rgba(255,255,255,0.06)] px-6 py-3 font-mono text-[13px] text-ash transition-colors hover:text-sinal-white"
          >
            {backLabel}
          </Link>
        </div>
      </div>
    </div>
  );
}

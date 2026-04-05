"use client";

import { useEffect } from "react";

export default function FeedError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[FeedPage] Error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center pt-[72px]">
      <div className="max-w-md text-center">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[2px] text-ash">Erro</p>
        <h1 className="mb-3 font-display text-[24px] text-sinal-white">
          Nao foi possivel carregar o feed
        </h1>
        <p className="mb-6 text-[14px] text-ash">
          Houve um problema ao buscar os sinais. Tente novamente em alguns instantes.
        </p>
        <button
          onClick={reset}
          className="rounded-lg bg-signal px-5 py-2.5 font-mono text-[13px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim"
        >
          Tentar novamente
        </button>
      </div>
    </div>
  );
}

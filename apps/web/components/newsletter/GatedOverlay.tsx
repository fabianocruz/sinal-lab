"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function GatedOverlay() {
  const pathname = usePathname();
  const callbackParam = pathname ? `?callbackUrl=${encodeURIComponent(pathname)}` : "";

  return (
    <div className="relative -mt-[100px]">
      {/* Gradient fade that overlaps the last visible paragraph by ~100px */}
      <div
        className="pointer-events-none h-[100px] w-full"
        style={{
          background: "linear-gradient(to bottom, transparent 0%, #0A0A0B 100%)",
        }}
        aria-hidden="true"
      />

      {/* Gate card */}
      <div className="bg-sinal-graphite rounded-xl border border-[rgba(255,255,255,0.06)] px-8 py-10 text-center">
        <h2 className="font-display text-[22px] leading-snug text-sinal-white">Continue lendo</h2>

        <p className="mt-3 text-[15px] leading-relaxed text-silver font-body">
          Crie sua conta gratuita para acessar todas as edições do Sinal.
        </p>

        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href={`/cadastro${callbackParam}`}
            className="w-full rounded-lg bg-signal px-6 py-3 text-center font-mono text-[13px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim sm:w-auto"
          >
            Criar conta gratuita
          </Link>

          <Link
            href={`/login${callbackParam}`}
            className="w-full rounded-lg border border-[rgba(255,255,255,0.06)] px-6 py-3 text-center font-mono text-[13px] text-sinal-white transition-colors hover:border-[rgba(255,255,255,0.15)] hover:bg-[rgba(255,255,255,0.04)] sm:w-auto"
          >
            Já tenho conta
          </Link>
        </div>

        <p className="mt-6 font-mono text-[11px] text-ash">
          Grátis. Sem spam. Cancele quando quiser.
        </p>
      </div>
    </div>
  );
}

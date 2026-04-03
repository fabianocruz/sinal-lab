"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const AGENT_COLORS = [
  "#59FFB4", // RADAR
  "#FF8A59", // FUNDING
  "#59B4FF", // CÓDIGO
  "#C459FF", // MERCADO
  "#E8FF59", // SÍNTESE
];

const VALUE_PROPS = [
  "Acesso completo a todas as edições",
  "5 relatórios semanais por agente de IA",
  "Newsletter no email toda semana",
];

export default function GatedOverlay() {
  const pathname = usePathname();
  const callbackParam = pathname ? `?callbackUrl=${encodeURIComponent(pathname)}` : "";

  return (
    <div className="relative -mt-[100px]">
      {/* Gradient fade that overlaps the last visible paragraph */}
      <div
        className="pointer-events-none h-[100px] w-full"
        style={{
          background: "linear-gradient(to bottom, transparent 0%, #0A0A0B 100%)",
        }}
        aria-hidden="true"
      />

      {/* Gate card */}
      <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-8 py-10">
        {/* Mini agent color bar */}
        <div className="mb-8 flex justify-center gap-1">
          {AGENT_COLORS.map((color) => (
            <div
              key={color}
              className="h-[3px] w-5 rounded-full"
              style={{ backgroundColor: color }}
              aria-hidden="true"
            />
          ))}
        </div>

        <h2 className="text-center font-display text-[22px] leading-snug text-sinal-white">
          Leia a análise completa
        </h2>

        {/* Value props */}
        <ul className="mt-5 space-y-2.5">
          {VALUE_PROPS.map((prop) => (
            <li
              key={prop}
              className="flex items-start gap-2.5 text-[14px] leading-relaxed text-silver"
            >
              <span
                className="mt-[7px] block h-[5px] w-[5px] shrink-0 rounded-full bg-signal"
                aria-hidden="true"
              />
              {prop}
            </li>
          ))}
        </ul>

        {/* CTAs */}
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

        <p className="mt-6 text-center font-mono text-[11px] text-ash">
          Grátis. Sem spam. Cancele quando quiser.
        </p>
      </div>
    </div>
  );
}

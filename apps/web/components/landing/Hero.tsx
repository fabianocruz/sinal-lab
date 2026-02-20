'use client';

import Link from 'next/link';
import WaitlistForm from './WaitlistForm';

const AVATARS = ['FC', 'ML', 'RB', 'AS', '+'];

export default function Hero() {
  return (
    <section
      id="hero"
      className="relative flex min-h-screen items-center overflow-hidden pt-[72px]"
    >
      {/* Background glows */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-[20%] -top-[30%] h-[70%] w-[70%]"
        style={{
          background: 'radial-gradient(ellipse, rgba(232,255,89,0.04) 0%, transparent 60%)',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-[20%] -left-[10%] h-[50%] w-[50%]"
        style={{
          background: 'radial-gradient(ellipse, rgba(89,255,180,0.02) 0%, transparent 60%)',
        }}
      />

      <div className="relative z-10 mx-auto max-w-container px-6 py-20 md:px-10">
        <div className="max-w-[720px]">
          {/* Label */}
          <div className="mb-6 flex items-center gap-2.5">
            <span className="block h-px w-6 bg-signal" />
            <span className="font-mono text-[12px] font-semibold uppercase tracking-[2.5px] text-signal">
              Inteligência tech LATAM
            </span>
          </div>

          {/* Headline */}
          <h1 className="mb-7 font-display text-[clamp(40px,6vw,72px)] font-normal leading-[1.08] tracking-[-0.02em] text-sinal-white">
            Inteligência <em className="italic text-signal">essencial,</em>
            <br />
            não superficial.
          </h1>

          {/* Subheadline */}
          <p className="mb-10 max-w-[580px] text-[clamp(17px,2vw,19px)] leading-[1.7] text-ash">
            Toda segunda-feira, os dados mais relevantes sobre o ecossistema
            tech da América Latina — pesquisados por centenas de agentes de IA
            auditáveis, revisados por humanos, entregues no seu inbox.
          </p>

          {/* Waitlist form */}
          <WaitlistForm className="mb-4 max-w-[480px]" />

          {/* Micro copy */}
          <p className="mb-12 text-[13px] text-sinal-slate">
            Grátis. Sem spam.{' '}
            <Link
              href="#edicoes"
              className="text-ash underline underline-offset-2 hover:text-sinal-white"
            >
              Ou comece pelo último Briefing →
            </Link>
          </p>

          {/* Social proof */}
          <div className="flex items-center gap-4 border-t border-[rgba(255,255,255,0.06)] pt-8">
            <div className="flex">
              {AVATARS.map((initials, i) => (
                <span
                  key={i}
                  className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-sinal-black bg-sinal-slate text-[11px] font-semibold text-ash"
                  style={{ marginRight: i < AVATARS.length - 1 ? '-8px' : '0' }}
                >
                  {initials}
                </span>
              ))}
            </div>
            <p className="text-[14px] text-ash">
              <strong className="font-semibold text-bone">+2.500</strong>{' '}
              fundadores, CTOs e investidores já leem o Sinal
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

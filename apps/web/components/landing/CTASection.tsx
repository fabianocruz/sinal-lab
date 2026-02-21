'use client';

import WaitlistForm from './WaitlistForm';

export default function CTASection() {
  return (
    <section className="border-b border-[rgba(255,255,255,0.04)] border-t bg-sinal-graphite">
      <div className="mx-auto max-w-container px-6 py-section md:px-10">
        <div className="text-center">
          {/* Section label */}
          <div className="mb-5 flex items-center justify-center gap-2.5">
            <span className="block h-px w-6 bg-signal" />
            <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
              Receba o sinal
            </span>
            <span className="block h-px w-6 bg-signal" />
          </div>

          <h2 className="mb-4 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
            Pronto para receber<br />inteligência de verdade?
          </h2>
          <p className="mx-auto mb-9 max-w-[600px] text-[17px] leading-[1.7] text-ash">
            O próximo Briefing sai na segunda-feira. Junte-se a milhares de
            fundadores, CTOs e investidores que começam a semana com os dados
            certos.
          </p>

          <WaitlistForm
            inputBg="black"
            buttonLabel="Assinar →"
            className="mx-auto mb-4 max-w-[440px]"
          />

          <p className="text-[12px] text-sinal-slate">
            Sem spam. Cancelamento em 1 clique. Seus dados nunca são vendidos.
          </p>
        </div>
      </div>
    </section>
  );
}

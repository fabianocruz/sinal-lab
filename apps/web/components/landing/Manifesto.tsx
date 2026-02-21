export default function Manifesto() {
  return (
    <section
      id="manifesto"
      className="border-b border-[rgba(255,255,255,0.04)] border-t bg-sinal-graphite py-section"
    >
      <div className="mx-auto max-w-container px-6 md:px-10">
        <div className="max-w-[640px]">
          {/* Section label */}
          <div className="mb-4 flex items-center gap-2.5">
            <span className="block h-px w-6 bg-signal" />
            <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
              Manifesto
            </span>
          </div>

          <h2 className="mb-8 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
            Por que construímos o Sinal.
          </h2>

          <p className="mb-5 text-[17px] leading-[1.8] text-silver">
            Informação é infraestrutura — tão essencial para quem constrói tecnologia na América
            Latina quanto energia elétrica ou banda larga.
          </p>

          <p className="mb-5 text-[17px] leading-[1.8] text-silver">
            Hoje, a inteligência de mercado que fundamenta as melhores decisões está fragmentada em
            plataformas pagas em inglês, redes informais de investidores e intuições que poucos
            compartilham.
          </p>

          <p className="mb-8 text-[17px] leading-[1.8] text-silver">
            O ecossistema que produz 3 milhões de desenvolvedores e 40.000 startups merece sua
            própria infraestrutura de inteligência — transparente, auditável, contínua e acessível a
            qualquer fundador técnico com a ambição de construir algo que importe.
          </p>

          <div className="font-display text-[20px] italic text-signal">
            Inteligência aberta para quem constrói.
          </div>
        </div>
      </div>
    </section>
  );
}

export default function BriefingExplainer() {
  return (
    <section
      id="briefing"
      className="border-b border-[rgba(255,255,255,0.04)] py-section"
    >
      <div className="mx-auto max-w-container px-6 md:px-10">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-2 md:gap-12 md:items-start">
          {/* Text column */}
          <div>
            <div className="mb-4 flex items-center gap-2.5">
              <span className="block h-px w-6 bg-signal" />
              <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
                O Briefing
              </span>
            </div>
            <h2 className="mb-6 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
              O que é o<br />Briefing Sinal?
            </h2>
            <p className="mb-4 text-[16px] leading-[1.7] text-silver">
              O <strong className="text-sinal-white">Briefing Sinal</strong> é
              uma curadoria semanal de inteligência de mercado sobre o
              ecossistema tech da América Latina. Não é um agregador de
              notícias — é uma análise estruturada, com dados verificáveis e
              contexto que você não encontra em nenhum outro lugar.
            </p>
            <p className="mb-6 text-[16px] leading-[1.7] text-silver">
              Cada seção é pesquisada por agentes de IA especializados,
              validada por múltiplas fontes e revisada por editores humanos
              antes de chegar ao seu inbox.
            </p>
            <a
              href="#hero"
              className="inline-flex items-center gap-2 text-[15px] font-semibold text-signal transition-[gap] duration-200 hover:gap-3"
            >
              Receba o próximo Briefing →
            </a>
          </div>

          {/* Newsletter preview card */}
          <div className="overflow-hidden rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] px-7 py-6">
              <div className="flex items-center gap-1.5 font-display text-[18px] text-sinal-white">
                <span className="inline-block h-[5px] w-[5px] rounded-full bg-signal" />
                Sinal Semanal
              </div>
              <div className="font-mono text-[10px] tracking-[0.5px] text-ash">
                Ed. #47 · 10 Fev 2026
              </div>
            </div>

            {/* SINTESE block */}
            <div className="border-b border-[rgba(255,255,255,0.06)] px-7 py-5">
              <div className="mb-2.5 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[2px]" style={{ color: '#E8FF59' }}>
                <span className="inline-block h-[5px] w-[5px] rounded-full" style={{ background: '#E8FF59' }} />
                SÍNTESE
              </div>
              <div className="mb-2 font-display text-[17px] leading-snug text-sinal-white">
                O paradoxo do modelo gratuito: quando abundância de IA vira commodity
              </div>
              <div className="text-[14px] leading-[1.6] text-ash">
                A avalanche de modelos open-source não é generosidade — é estratégia de comoditização da camada de inferência.
              </div>
            </div>

            {/* RADAR block */}
            <div className="border-b border-[rgba(255,255,255,0.06)] px-7 py-5">
              <div className="mb-2.5 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[2px]" style={{ color: '#59FFB4' }}>
                <span className="inline-block h-[5px] w-[5px] rounded-full" style={{ background: '#59FFB4' }} />
                RADAR
              </div>
              <div className="mb-2 font-display text-[17px] leading-snug text-sinal-white">
                3 padrões emergentes desta semana
              </div>
              <div className="font-mono text-[13px] leading-[1.8] text-silver">
                ↗ AI agents em compliance regulatório LATAM<br />
                ↗ Migração de devs para Rust em infra de pagamentos<br />
                ↘ Interesse de VCs em crypto-native fintech
              </div>
            </div>

            {/* FUNDING block */}
            <div className="border-b border-[rgba(255,255,255,0.06)] px-7 py-5">
              <div className="mb-2.5 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[2px]" style={{ color: '#FF8A59' }}>
                <span className="inline-block h-[5px] w-[5px] rounded-full" style={{ background: '#FF8A59' }} />
                FUNDING
              </div>
              <div className="rounded-r-md border-l-2 bg-[rgba(255,138,89,0.05)] py-3 pl-3.5 pr-3.5" style={{ borderLeftColor: '#FF8A59' }}>
                <div className="font-mono text-[12px] leading-[1.8] text-silver">
                  Serie B · Clip (MEX) · $50M · SoftBank<br />
                  Serie A · Pomelo (ARG) · $18M · Kaszek<br />
                  <span className="text-ash">+ 10 rodadas →</span>
                </div>
              </div>
            </div>

            {/* MERCADO block */}
            <div className="px-7 py-5">
              <div className="mb-2.5 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[2px]" style={{ color: '#C459FF' }}>
                <span className="inline-block h-[5px] w-[5px] rounded-full" style={{ background: '#C459FF' }} />
                MERCADO
              </div>
              <div className="rounded-r-md border-l-2 bg-[rgba(196,89,255,0.05)] py-3 pl-3.5 pr-3.5" style={{ borderLeftColor: '#C459FF' }}>
                <div className="font-mono text-[12px] leading-[1.8] text-silver">
                  Launch · Koywe 2.0 (CHL) · Crypto Rails<br />
                  Acquisition · Dock + processadora Peru<br />
                  <span className="text-ash">+ 5 movimentos →</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

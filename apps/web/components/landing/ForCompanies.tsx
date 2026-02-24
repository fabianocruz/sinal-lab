const B2B_CARDS = [
  {
    title: "Relatórios setoriais sob demanda",
    desc: "Deep dives personalizados sobre verticais, mercados ou tecnologias específicas. Co-branded com sua empresa.",
  },
  {
    title: "API de dados LATAM",
    desc: "Acesso programático a perfis de startups, dados de funding, índices e tendências. Integre na sua plataforma.",
  },
  {
    title: "Inteligência competitiva contínua",
    desc: "Monitoramento de concorrentes, movimentações e oportunidades de M&A — atualizado semanalmente.",
  },
];

export default function ForCompanies() {
  return (
    <section id="empresas" className="border-b border-[rgba(255,255,255,0.04)] py-section">
      <div className="mx-auto max-w-container px-6 md:px-10">
        {/* Section label */}
        <div className="mb-4 flex items-center gap-2.5">
          <span className="block h-px w-6 bg-signal" />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
            Para empresas
          </span>
        </div>

        <h2 className="mb-5 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
          Sinal para empresas.
        </h2>
        <p className="mb-10 max-w-[600px] text-[17px] leading-[1.7] text-ash">
          Equipes de estratégia, corporate venture e M&A usam o Sinal para tomar decisões baseadas
          em dados sobre o ecossistema tech da América Latina.
        </p>

        <div className="mb-10 grid grid-cols-1 gap-5 sm:grid-cols-2 md:grid-cols-3">
          {B2B_CARDS.map((card) => (
            <div
              key={card.title}
              className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-6 py-8"
            >
              <h4 className="mb-2.5 text-[16px] font-semibold text-sinal-white">{card.title}</h4>
              <p className="text-[14px] leading-[1.6] text-ash">{card.desc}</p>
            </div>
          ))}
        </div>

        <a
          href="/contato?topic=parceria"
          className="inline-flex items-center gap-2 rounded-[10px] border border-sinal-slate px-7 py-3.5 text-[14px] font-semibold text-sinal-white transition-colors duration-200 hover:border-silver"
        >
          Fale com nosso time →
        </a>
      </div>
    </section>
  );
}

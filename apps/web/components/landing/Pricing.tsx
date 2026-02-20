const PRICING_TIERS = [
  {
    name: 'Briefing',
    price: 'R$0',
    period: 'Grátis, para sempre.',
    features: [
      'Briefing semanal por email',
      'Acesso ao arquivo de edições',
      'Newsletter com dados e análises',
      'Índices públicos LATAM',
    ],
    cta: 'Assinar grátis',
    ctaVariant: 'secondary' as const,
    featured: false,
  },
  {
    name: 'Pro',
    price: 'R$29',
    period: 'ou R$249/ano (economize 28%)',
    features: [
      'Tudo do Briefing, mais:',
      'Deep dives mensais exclusivos',
      'Alertas de deals e tendências',
      'Acesso à comunidade de builders',
      'Dados exportáveis (CSV/API)',
      'Perfis detalhados de 500+ startups',
    ],
    cta: 'Começar Pro',
    ctaVariant: 'primary' as const,
    featured: true,
  },
  {
    name: 'Founding Member',
    price: 'R$79',
    period: 'Vagas limitadas.',
    priceSuffix: '/ano',
    features: [
      'Tudo do Pro, mais:',
      'Nome na página de fundadores',
      'Acesso antecipado a features',
      'Convite para eventos exclusivos',
      'Voto em prioridades do roadmap',
      'Badge "Founding Member"',
    ],
    cta: 'Seja um Founding Member →',
    ctaVariant: 'secondary' as const,
    featured: false,
  },
];

export default function Pricing() {
  return (
    <section
      id="precos"
      className="border-b border-[rgba(255,255,255,0.04)] py-section"
    >
      <div className="mx-auto max-w-container px-6 md:px-10">
        {/* Section label */}
        <div className="mb-4 flex items-center gap-2.5">
          <span className="block h-px w-6 bg-signal" />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
            Preços
          </span>
        </div>

        <h2 className="mb-5 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
          Quanto custa?
        </h2>
        <p className="mb-12 max-w-[600px] text-[17px] leading-[1.7] text-ash">
          Inteligência de mercado não deveria ser privilégio de quem paga
          US$50.000/ano por um terminal. O Sinal nasceu aberto.
        </p>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {PRICING_TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`relative flex flex-col rounded-2xl border bg-sinal-graphite p-9 ${
                tier.featured
                  ? 'border-signal'
                  : 'border-[rgba(255,255,255,0.06)]'
              }`}
            >
              {tier.featured && (
                <span className="absolute -top-3 left-7 rounded bg-signal px-3 py-1 font-mono text-[10px] font-semibold uppercase tracking-[1.5px] text-sinal-black">
                  Recomendado
                </span>
              )}

              <div className="mb-4 font-mono text-[12px] uppercase tracking-[2px] text-ash">
                {tier.name}
              </div>

              <div className="mb-1 font-display text-[36px] text-sinal-white">
                {tier.price}{' '}
                <span className="font-body text-[15px] font-normal text-ash">
                  {tier.priceSuffix ?? '/mês'}
                </span>
              </div>

              <div className="mb-7 text-[13px] text-ash">{tier.period}</div>

              <ul className="mb-8 flex-1 space-y-0">
                {tier.features.map((feature) => (
                  <li
                    key={feature}
                    className="relative border-b border-[rgba(255,255,255,0.03)] py-2 pl-5 text-[14px] text-silver"
                  >
                    <span className="absolute left-0 top-[14px] inline-block h-1.5 w-1.5 rounded-full bg-signal opacity-50" />
                    {feature}
                  </li>
                ))}
              </ul>

              <a
                href="#hero"
                className={`block rounded-[10px] border py-3.5 text-center text-[14px] font-semibold transition-all duration-200 ${
                  tier.ctaVariant === 'primary'
                    ? 'border-signal bg-signal text-sinal-black hover:bg-signal-dim'
                    : 'border-sinal-slate bg-transparent text-sinal-white hover:border-silver'
                }`}
              >
                {tier.cta}
              </a>
            </div>
          ))}
        </div>

        <p className="mx-auto mt-8 max-w-[560px] text-center text-[14px] italic text-ash">
          Os dados que importam são abertos. Sempre serão. A assinatura Pro
          financia a pesquisa — não tranca o acesso.
        </p>
      </div>
    </section>
  );
}

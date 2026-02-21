const METRICS = [
  { number: '87%', label: 'dos assinantes abrem toda semana' },
  { number: '4.8', suffix: '/5', label: 'avaliação média dos leitores' },
  { number: '92%', label: 'recomendariam a um colega' },
];

const TESTIMONIALS = [
  {
    text: 'Eu gastava horas por semana tentando montar um panorama do ecossistema. O Sinal faz isso em 5 minutos, com fontes que eu posso verificar.',
    author: 'CTO',
    company: 'Startup Series B, São Paulo',
  },
  {
    text: 'Como investidor, preciso de dados confiáveis sobre LATAM. O Sinal é a única fonte que mostra a metodologia de tudo que publica.',
    author: 'Partner',
    company: 'VC Fund, São Paulo',
  },
  {
    text: 'A transparência dos agentes de IA é o que diferencia. Sei exatamente o que é dado bruto e o que é análise.',
    author: 'Fundador',
    company: 'Startup, Florianópolis',
  },
  {
    text: 'O Deep Dive sobre embedded finance me poupou duas semanas de research. E os dados estavam todos lá, verificáveis.',
    author: 'Head de Produto',
    company: 'Fintech, Recife',
  },
];

export default function SocialProof() {
  return (
    <section className="border-b border-[rgba(255,255,255,0.04)] py-section">
      <div className="mx-auto max-w-container px-6 md:px-10">
        {/* Section label */}
        <div className="mb-4 flex items-center gap-2.5">
          <span className="block h-px w-6 bg-signal" />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
            Quem lê
          </span>
        </div>

        <h2 className="mb-5 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
          Quem constrói tecnologia na<br />América Latina já lê o Sinal.
        </h2>
        <p className="mb-14 text-[17px] leading-[1.7] text-ash">
          Veja o que dizem.
        </p>

        {/* Metrics */}
        <div className="mb-14 grid grid-cols-1 gap-6 sm:grid-cols-3">
          {METRICS.map((metric) => (
            <div
              key={metric.label}
              className="rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-5 py-8 text-center"
            >
              <div className="mb-2 font-display text-[clamp(36px,5vw,52px)] text-sinal-white">
                {metric.number}
                {metric.suffix && (
                  <span className="font-body text-[20px] text-ash">
                    {metric.suffix}
                  </span>
                )}
              </div>
              <div className="text-[14px] text-ash">{metric.label}</div>
            </div>
          ))}
        </div>

        {/* Testimonials */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {TESTIMONIALS.map((t) => (
            <div
              key={t.author + t.company}
              className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-7"
            >
              <p className="mb-5 text-[15px] italic leading-[1.7] text-bone">
                &ldquo;{t.text}&rdquo;
              </p>
              <p className="text-[13px] text-ash">
                <strong className="font-semibold not-italic text-silver">
                  {t.author}
                </strong>{' '}
                · {t.company}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

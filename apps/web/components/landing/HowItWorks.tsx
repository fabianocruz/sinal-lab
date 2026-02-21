const PIPELINE_STEPS = [
  {
    num: '01',
    title: 'Pesquisa',
    desc: 'Centenas de agentes especializados coletam dados de fontes públicas e verificáveis em 3 idiomas.',
  },
  {
    num: '02',
    title: 'Validação',
    desc: 'Cruzamento com múltiplas fontes. Score de qualidade A/B/C/D para cada dado.',
  },
  {
    num: '03',
    title: 'Verificação',
    desc: 'Checagem de fatos, consistência numérica e temporal automatizada.',
  },
  {
    num: '04',
    title: 'Detecção de viés',
    desc: 'Identificação de vieses geográficos, setoriais e de estágio.',
  },
  {
    num: '05',
    title: 'Síntese',
    desc: 'Montagem editorial com voz da marca, contexto e opinião fundamentada.',
  },
  {
    num: '06',
    title: 'Revisão humana',
    desc: 'Editor revisa tudo antes de qualquer publicação. Sempre.',
  },
];

export default function HowItWorks() {
  return (
    <section
      id="metodologia"
      className="border-b border-[rgba(255,255,255,0.04)] py-section"
    >
      <div className="mx-auto max-w-container px-6 md:px-10">
        {/* Section label */}
        <div className="mb-4 flex items-center gap-2.5">
          <span className="block h-px w-6 bg-signal" />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
            Metodologia
          </span>
        </div>

        <h2 className="mb-5 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
          Inteligência de IA com<br />transparência radical.
        </h2>
        <p className="mb-12 max-w-[600px] text-[17px] leading-[1.7] text-ash">
          Nossos agentes de IA não são caixas-pretas. Cada um tem nome, função
          documentada e metodologia publicada. Você sempre sabe o que foi
          gerado por máquina e o que foi revisado por humano.
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
          {PIPELINE_STEPS.map((step) => (
            <div
              key={step.num}
              className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-6 py-7"
            >
              <div className="mb-3 font-mono text-[11px] font-semibold tracking-[1px] text-signal">
                {step.num}
              </div>
              <h4 className="mb-2 text-[15px] font-semibold text-sinal-white">
                {step.title}
              </h4>
              <p className="text-[14px] leading-[1.55] text-ash">{step.desc}</p>
            </div>
          ))}
        </div>

        {/* Quality badge */}
        <div className="mt-8 inline-flex items-center gap-2 rounded-lg bg-[rgba(232,255,89,0.06)] px-4 py-2 font-mono text-[12px] text-signal">
          <span className="inline-block h-[5px] w-[5px] rounded-full bg-signal" />
          DQ: 4/5 · AC: 4/5 · Revisado por editor
        </div>
      </div>
    </section>
  );
}

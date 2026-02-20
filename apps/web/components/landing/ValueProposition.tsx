const VALUE_CARDS = [
  {
    icon: '⊘',
    title: 'Informação verificável,\nnão opinião.',
    desc: 'Cada dado publicado tem fonte rastreável, score de confiança e metodologia aberta. Você sabe exatamente de onde vem cada número.',
  },
  {
    icon: '◷',
    title: 'Economize 5 horas\npor semana.',
    desc: 'Agentes de IA vasculham dezenas de fontes em português, inglês e espanhol para entregar só o que importa. Menos ruído, mais decisão.',
  },
  {
    icon: '◎',
    title: 'O ecossistema inteiro,\na um clique.',
    desc: 'De São Paulo a Cidade do México, de pré-seed a Série C — startups, tendências, funding e tecnologias emergentes em toda a América Latina.',
  },
];

export default function ValueProposition() {
  return (
    <section className="border-b border-[rgba(255,255,255,0.04)] py-section">
      <div className="mx-auto max-w-container px-6 md:px-10">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {VALUE_CARDS.map((card) => (
            <div
              key={card.title}
              className="rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-9 transition-transform duration-200 hover:-translate-y-0.5"
            >
              <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-[10px] bg-[rgba(232,255,89,0.06)] text-[20px]">
                {card.icon}
              </div>
              <h3 className="mb-3 whitespace-pre-line font-body text-[17px] font-semibold leading-snug text-sinal-white">
                {card.title}
              </h3>
              <p className="text-[15px] leading-relaxed text-ash">{card.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

import Section from './Section';

export default function SocialProof() {
  const metrics = [
    {
      value: '87%',
      label: 'dos assinantes abrem toda semana',
      quote: 'É o único email que leio antes do café.'
    },
    {
      value: '4.8/5',
      label: 'avaliação média dos leitores',
      quote: 'Finalmente alguém mapeou o ecossistema com dados, não com achismo.'
    },
    {
      value: '92%',
      label: 'recomendariam a um colega',
      quote: 'Compartilho com meu time inteiro toda segunda.'
    }
  ];

  const testimonials = [
    {
      text: 'Eu gastava horas por semana tentando montar um panorama do ecossistema. O Sinal faz isso em 5 minutos, com fontes que eu posso verificar.',
      author: 'CTO',
      company: 'Startup Series B, São Paulo'
    },
    {
      text: 'Como investidor, preciso de dados confiáveis sobre LATAM. O Sinal é a única fonte que mostra a metodologia de tudo que publica.',
      author: 'Partner',
      company: 'VC Fund, São Paulo'
    },
    {
      text: 'A transparência dos agentes de IA é o que diferencia. Sei exatamente o que é dado bruto e o que é análise. Nenhuma outra newsletter faz isso.',
      author: 'Fundador',
      company: 'Startup, Florianópolis'
    },
    {
      text: 'O Deep Dive sobre embedded finance me poupou duas semanas de research. E os dados estavam todos lá, verificáveis.',
      author: 'Head de Produto',
      company: 'Fintech, Recife'
    }
  ];

  return (
    <Section className="bg-gray-50">
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold mb-4">
          Quem constrói tecnologia na América Latina já lê o Sinal.
        </h2>
        <p className="text-lg text-gray-700">Veja o que dizem.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-8 mb-16">
        {metrics.map((metric, index) => (
          <div key={index} className="text-center">
            <div className="text-5xl font-bold text-red-600 mb-2">{metric.value}</div>
            <p className="text-sm font-medium text-gray-900 mb-3">{metric.label}</p>
            <p className="text-sm text-gray-600 italic">"{metric.quote}"</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {testimonials.map((testimonial, index) => (
          <div key={index} className="bg-white border border-gray-200 rounded-lg p-6">
            <p className="text-gray-700 mb-4 leading-relaxed">"{testimonial.text}"</p>
            <div className="text-sm">
              <span className="font-bold">{testimonial.author}</span>
              <span className="text-gray-600"> · {testimonial.company}</span>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

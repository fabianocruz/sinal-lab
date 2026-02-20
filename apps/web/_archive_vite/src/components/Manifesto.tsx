import Section from './Section';

export default function Manifesto() {
  return (
    <Section dark>
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-4xl font-bold mb-8">Por que construímos o Sinal.</h2>

        <div className="space-y-6 text-lg text-gray-300 leading-relaxed">
          <p>
            Informação é infraestrutura — tão essencial para quem constrói tecnologia na América Latina
            quanto energia elétrica ou banda larga.
          </p>

          <p>
            Hoje, a inteligência de mercado que fundamenta as melhores decisões está fragmentada em plataformas
            pagas em inglês, redes informais de investidores e intuições que poucos compartilham.
          </p>

          <p>
            O ecossistema que produz 3 milhões de desenvolvedores e 40.000 startups merece sua própria
            infraestrutura de inteligência — transparente, auditável, contínua e acessível a qualquer
            fundador técnico com a ambição de construir algo que importe.
          </p>

          <p className="text-xl font-bold text-white mt-8">
            Inteligência aberta para quem constrói.
          </p>
        </div>
      </div>
    </Section>
  );
}

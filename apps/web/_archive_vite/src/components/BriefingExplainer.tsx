import Section from './Section';
import Button from './Button';

export default function BriefingExplainer() {
  return (
    <Section className="bg-gray-50" id="briefing">
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold mb-6">O que é o Briefing Sinal?</h2>
        <p className="text-lg text-gray-700 max-w-3xl mx-auto leading-relaxed">
          O <strong>Briefing Sinal</strong> é uma curadoria semanal de inteligência de mercado sobre o ecossistema tech da América Latina.
          Não é um agregador de notícias — é uma análise estruturada, com dados verificáveis e contexto que você não encontra em nenhum outro lugar.
        </p>
      </div>

      <div className="max-w-3xl mx-auto bg-white border-2 border-gray-200 rounded-lg p-8 mb-8">
        <div className="mb-6">
          <div className="text-sm text-gray-500 mb-2">BRIEFING SINAL · Edição #47 · 10 de fevereiro de 2026</div>
        </div>

        <div className="space-y-6">
          <div>
            <div className="text-xl font-bold mb-3">📡 RADAR DA SEMANA</div>
            <p className="text-gray-700">
              3 deals acima de US$50M que passaram despercebidos · A vertical de healthtech que cresceu 340% em 12 meses ·
              O que o novo marco regulatório de IA significa para startups brasileiras
            </p>
          </div>

          <div className="border-t border-gray-200 pt-6">
            <div className="text-xl font-bold mb-3">📊 DADOS DA SEMANA</div>
            <p className="text-gray-700 mb-2">
              <strong>Funding LATAM:</strong> US$287M em 14 deals (−12% vs. semana anterior)
            </p>
            <p className="text-gray-700">
              <strong>Destaque:</strong> Fintech segue liderando, mas edtech recuperou participação pela primeira vez em 8 meses
            </p>
          </div>

          <div className="border-t border-gray-200 pt-6">
            <div className="text-xl font-bold mb-3">🔬 DEEP DIVE</div>
            <p className="text-gray-700">
              Por que o embedded finance B2B está prestes a explodir na América Latina — e quem está melhor posicionado
            </p>
          </div>
        </div>
      </div>

      <p className="text-center text-gray-600 mb-8 max-w-2xl mx-auto">
        Cada seção é pesquisada por agentes de IA especializados, validada por múltiplas fontes e revisada por editores humanos antes de chegar ao seu inbox.
      </p>

      <div className="text-center">
        <Button size="lg">Receba o próximo Briefing →</Button>
      </div>
    </Section>
  );
}

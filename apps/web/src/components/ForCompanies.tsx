import { FileText, Database, TrendingUp } from 'lucide-react';
import Section from './Section';
import Button from './Button';

export default function ForCompanies() {
  const benefits = [
    {
      icon: FileText,
      title: 'Relatórios setoriais sob demanda',
      description: 'Deep dives personalizados sobre verticais, mercados ou tecnologias específicas. Co-branded com sua empresa.'
    },
    {
      icon: Database,
      title: 'API de dados LATAM',
      description: 'Acesso programático a perfis de startups, dados de funding, índices e tendências. Integre na sua plataforma de inteligência.'
    },
    {
      icon: TrendingUp,
      title: 'Inteligência competitiva contínua',
      description: 'Monitoramento de concorrentes, movimentações de mercado e oportunidades de M&A — atualizado semanalmente.'
    }
  ];

  return (
    <Section className="bg-gray-50" id="empresas">
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold mb-6">Sinal para empresas.</h2>
        <p className="text-lg text-gray-700 max-w-3xl mx-auto leading-relaxed">
          Equipes de estratégia, corporate venture e M&A usam o Sinal para tomar decisões baseadas em dados sobre
          o ecossistema tech da América Latina.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-8 mb-12">
        {benefits.map((benefit, index) => (
          <div key={index} className="bg-white border border-gray-200 rounded-lg p-8">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-red-100 rounded-lg mb-4">
              <benefit.icon className="w-6 h-6 text-red-600" />
            </div>
            <h3 className="text-xl font-bold mb-3">{benefit.title}</h3>
            <p className="text-gray-700 leading-relaxed">{benefit.description}</p>
          </div>
        ))}
      </div>

      <div className="text-center">
        <Button size="lg">Fale com nosso time →</Button>
        <p className="text-sm text-gray-600 mt-6">Usado por equipes de estratégia em empresas líderes do mercado</p>
      </div>
    </Section>
  );
}

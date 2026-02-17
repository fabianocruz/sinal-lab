import { Check } from 'lucide-react';
import Section from './Section';
import Button from './Button';

export default function Pricing() {
  const plans = [
    {
      name: 'Briefing',
      price: 'R$0',
      period: '/mês',
      description: 'Inteligência essencial para começar',
      features: [
        'Briefing semanal por email',
        'Acesso ao arquivo de edições',
        'Newsletter com dados e análises',
        'Índices públicos LATAM'
      ],
      cta: 'Assinar grátis',
      highlighted: false
    },
    {
      name: 'Pro',
      price: 'R$29',
      period: '/mês',
      priceAnnual: 'ou R$249/ano (economize 28%)',
      description: 'Para quem toma decisões com dados',
      features: [
        'Tudo do Briefing, mais:',
        'Deep dives mensais exclusivos',
        'Alertas de deals e tendências em tempo real',
        'Acesso à comunidade de builders',
        'Dados exportáveis (CSV/API)',
        'Perfis detalhados de 500+ startups'
      ],
      cta: 'Começar Pro',
      highlighted: true,
      badge: 'Recomendado'
    },
    {
      name: 'Founding Member',
      price: 'R$79',
      period: '/ano',
      description: 'Apoie o laboratório desde o início',
      features: [
        'Tudo do Pro, mais:',
        'Nome na página de fundadores',
        'Acesso antecipado a novos agentes',
        'Convite para eventos exclusivos',
        'Voto em prioridades do roadmap',
        'Badge "Founding Member"'
      ],
      cta: 'Seja um Founding Member →',
      highlighted: false,
      badge: 'Vagas limitadas'
    }
  ];

  return (
    <Section id="precos">
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold mb-6">Quanto custa?</h2>
        <p className="text-lg text-gray-700 max-w-3xl mx-auto leading-relaxed">
          Inteligência de mercado não deveria ser privilégio de quem paga US$50.000/ano por um terminal.
          O Sinal nasceu aberto.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-8 mb-12">
        {plans.map((plan, index) => (
          <div
            key={index}
            className={`relative border-2 rounded-lg p-8 ${
              plan.highlighted
                ? 'border-red-600 shadow-xl scale-105'
                : 'border-gray-200'
            }`}
          >
            {plan.badge && (
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                <span className={`px-4 py-1 text-sm font-medium rounded-full ${
                  plan.highlighted
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-800 text-white'
                }`}>
                  {plan.badge}
                </span>
              </div>
            )}

            <div className="text-center mb-6">
              <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
              <div className="mb-2">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-gray-600">{plan.period}</span>
              </div>
              {plan.priceAnnual && (
                <p className="text-sm text-gray-600">{plan.priceAnnual}</p>
              )}
              <p className="text-sm text-gray-600 mt-2">{plan.description}</p>
            </div>

            <ul className="space-y-3 mb-8">
              {plan.features.map((feature, featureIndex) => (
                <li key={featureIndex} className="flex items-start">
                  <Check className="w-5 h-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>

            <Button
              variant={plan.highlighted ? 'primary' : 'outline'}
              className="w-full"
            >
              {plan.cta}
            </Button>
          </div>
        ))}
      </div>

      <p className="text-center text-gray-600 italic mb-8">
        Os dados que importam são abertos. Sempre serão. A assinatura Pro financia a pesquisa — não tranca o acesso.
      </p>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <div className="text-center mb-4">
          <p className="text-sm font-medium text-gray-700">Fontes de dados:</p>
        </div>
        <div className="flex flex-wrap justify-center gap-6 items-center text-sm text-gray-600">
          <span>GitHub</span>
          <span>·</span>
          <span>arXiv</span>
          <span>·</span>
          <span>Crunchbase</span>
          <span>·</span>
          <span>Google Trends</span>
          <span>·</span>
          <span>HackerNews</span>
          <span>·</span>
          <span>Dados públicos LATAM</span>
        </div>
      </div>
    </Section>
  );
}

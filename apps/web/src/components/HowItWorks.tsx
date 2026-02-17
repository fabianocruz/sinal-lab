import { Search, CheckCircle2, Shield, AlertTriangle, FileText, User } from 'lucide-react';
import Section from './Section';
import Button from './Button';

export default function HowItWorks() {
  const steps = [
    {
      icon: Search,
      label: 'PESQUISA',
      description: 'Agente coleta dados de fontes públicas e verificáveis'
    },
    {
      icon: CheckCircle2,
      label: 'VALIDAÇÃO',
      description: 'Cruzamento com múltiplas fontes · Score de qualidade A/B/C/D'
    },
    {
      icon: Shield,
      label: 'VERIFICAÇÃO',
      description: 'Checagem de fatos, consistência numérica e temporal'
    },
    {
      icon: AlertTriangle,
      label: 'VIÉS',
      description: 'Detecção de vieses geográficos, setoriais e de estágio'
    },
    {
      icon: FileText,
      label: 'SÍNTESE',
      description: 'Montagem editorial com voz da marca e contexto'
    },
    {
      icon: User,
      label: 'REVISÃO HUMANA',
      description: 'Editor revisa antes de qualquer publicação'
    }
  ];

  return (
    <Section dark id="metodologia">
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold mb-6">Inteligência de IA com transparência radical.</h2>
        <p className="text-lg text-gray-300 max-w-3xl mx-auto leading-relaxed">
          Nossos agentes de IA não são caixas-pretas. Cada um tem nome, função documentada e metodologia publicada.
          Você sempre sabe o que foi gerado por máquina e o que foi revisado por humano.
        </p>
      </div>

      <div className="max-w-5xl mx-auto mb-12">
        <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-6">
          {steps.map((step, index) => (
            <div key={index} className="text-center">
              <div className="relative">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-red-600 rounded-full mb-4">
                  <step.icon className="w-8 h-8 text-white" />
                </div>
                {index < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-8 left-full w-full h-0.5 bg-gray-700"></div>
                )}
              </div>
              <div className="font-bold text-sm mb-2">{step.label}</div>
              <p className="text-sm text-gray-400">{step.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="text-center mb-8">
        <div className="inline-block bg-gray-800 border border-gray-700 rounded-lg px-6 py-3">
          <span className="text-sm font-mono">DQ: 4/5 · AC: 4/5 · Revisado por editor</span>
        </div>
      </div>

      <div className="text-center">
        <Button variant="primary">Leia nossa metodologia completa →</Button>
      </div>
    </Section>
  );
}

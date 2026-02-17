import { Shield, Clock, Map } from 'lucide-react';
import Section from './Section';

export default function ValueProposition() {
  const values = [
    {
      icon: Shield,
      title: 'Informação verificável, não opinião',
      description: 'Cada dado publicado tem fonte rastreável, score de confiança e metodologia aberta. Você sabe exatamente de onde vem cada número — e pode verificar por conta própria.'
    },
    {
      icon: Clock,
      title: 'Economize 5 horas por semana',
      description: 'Nossos agentes de IA vasculham dezenas de fontes em português, inglês e espanhol para entregar só o que importa. Menos ruído, mais decisão.'
    },
    {
      icon: Map,
      title: 'O ecossistema inteiro, a um clique',
      description: 'De São Paulo a Cidade do México, de pré-seed a Série C — mapeamos startups, tendências, funding e tecnologias emergentes em toda a América Latina.'
    }
  ];

  return (
    <Section>
      <div className="grid md:grid-cols-3 gap-12">
        {values.map((value, index) => (
          <div key={index} className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-6">
              <value.icon className="w-8 h-8 text-red-600" />
            </div>
            <h3 className="text-xl font-bold mb-4">{value.title}</h3>
            <p className="text-gray-700 leading-relaxed">{value.description}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

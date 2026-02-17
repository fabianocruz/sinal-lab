import { Calendar } from 'lucide-react';
import Section from './Section';

export default function EditionsPreviews() {
  const editions = [
    {
      date: '10/02/2026',
      number: '#47',
      title: 'Healthtech LATAM: a vertical silenciosa que cresceu 340%'
    },
    {
      date: '03/02/2026',
      number: '#46',
      title: 'US$1.2B em deals no Q4: quem captou, de quem, e por quê'
    },
    {
      date: '27/01/2026',
      number: '#45',
      title: 'O mapa de calor do talento técnico na América Latina'
    }
  ];

  return (
    <Section>
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold mb-6">
          Veja o Briefing com seus próprios olhos.
        </h2>
        <p className="text-lg text-gray-700 max-w-3xl mx-auto leading-relaxed">
          Não pedimos que confie em nós. Pedimos que verifique. Aqui estão as últimas edições — com todas as fontes,
          metodologias e scores de confiança.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {editions.map((edition, index) => (
          <div key={index} className="border-2 border-gray-200 rounded-lg p-6 hover:border-red-600 transition-colors cursor-pointer">
            <div className="flex items-center text-sm text-gray-600 mb-3">
              <Calendar className="w-4 h-4 mr-2" />
              {edition.date} · Edição {edition.number}
            </div>
            <h3 className="font-bold text-lg mb-4">{edition.title}</h3>
            <button className="text-red-600 font-medium hover:underline">
              Ler edição →
            </button>
          </div>
        ))}
      </div>
    </Section>
  );
}

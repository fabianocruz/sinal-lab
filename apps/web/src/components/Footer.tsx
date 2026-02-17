import { Search } from 'lucide-react';

export default function Footer() {
  const sections = [
    {
      title: 'Produto',
      links: [
        'Briefing Semanal',
        'Índices LATAM',
        'Deep Dives',
        'API de Dados',
        'Para Empresas'
      ]
    },
    {
      title: 'Comunidade',
      links: [
        'Comunidade de Builders',
        'Embaixadores Locais',
        'Painel de Especialistas',
        'Contribua com Dados'
      ]
    },
    {
      title: 'Transparência',
      links: [
        'Metodologia',
        'Fontes de Dados',
        'Log de Correções',
        'Dashboard de Viés',
        'Changelog dos Agentes'
      ]
    },
    {
      title: 'Institucional',
      links: [
        'Sobre',
        'Manifesto',
        'Imprensa',
        'Contato',
        'Termos',
        'Privacidade (LGPD)'
      ]
    }
  ];

  return (
    <footer className="bg-black text-white pt-16 pb-8">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid md:grid-cols-5 gap-8 mb-12">
          <div>
            <div className="text-2xl font-bold mb-4">SINAL</div>
            <p className="text-sm text-gray-400 mb-4">
              Inteligência aberta para quem constrói.
            </p>
          </div>

          {sections.map((section, index) => (
            <div key={index}>
              <h3 className="font-bold mb-4">{section.title}</h3>
              <ul className="space-y-2">
                {section.links.map((link, linkIndex) => (
                  <li key={linkIndex}>
                    <a href="#" className="text-sm text-gray-400 hover:text-white transition-colors">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row justify-between items-center">
          <div className="text-sm text-gray-400 mb-4 md:mb-0">
            © 2026 Sinal. Todos os direitos reservados.
          </div>

          <div className="flex items-center space-x-6 text-sm text-gray-400 mb-4 md:mb-0">
            <a href="#" className="hover:text-white transition-colors">LinkedIn</a>
            <a href="#" className="hover:text-white transition-colors">Twitter/X</a>
            <a href="#" className="hover:text-white transition-colors">GitHub</a>
          </div>
        </div>

        <div className="text-center mt-8 pt-8 border-t border-gray-800">
          <div className="inline-flex items-center text-sm text-gray-400">
            <Search className="w-4 h-4 mr-2" />
            Transparência radical. Metodologia aberta. Dados verificáveis.
          </div>
        </div>
      </div>
    </footer>
  );
}

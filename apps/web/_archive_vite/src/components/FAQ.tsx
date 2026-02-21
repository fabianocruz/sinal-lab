import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import Section from './Section';

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs = [
    {
      question: 'O que exatamente é o Sinal?',
      answer: 'O Sinal é um laboratório aberto de pesquisa e inteligência de mercado sobre o ecossistema tech da América Latina. Produzimos um Briefing semanal, índices públicos, deep dives e dados verificáveis — tudo pesquisado por agentes de IA auditáveis e revisado por editores humanos.'
    },
    {
      question: 'Como vocês usam inteligência artificial?',
      answer: 'Nossos agentes de IA têm nomes, funções documentadas e metodologias publicadas. Eles coletam dados, cruzam fontes, checam fatos e detectam vieses. Mas nenhum conteúdo é publicado sem revisão humana. Na página de Transparência, você vê exatamente o que foi gerado por IA e o que foi editado por humanos.'
    },
    {
      question: 'O Briefing é realmente gratuito?',
      answer: 'Sim. O Briefing semanal é e sempre será gratuito. Acreditamos que inteligência de mercado é infraestrutura — não produto de luxo. A assinatura Pro financia pesquisa mais profunda, não tranca o acesso aos dados essenciais.'
    },
    {
      question: 'Como vocês ganham dinheiro?',
      answer: 'Três fontes: assinaturas Pro de leitores individuais, relatórios co-branded para empresas, e API de dados para plataformas corporativas. Não vendemos dados de leitores e não aceitamos conteúdo patrocinado disfarçado de editorial.'
    },
    {
      question: 'Posso confiar nos dados?',
      answer: 'Cada dado publicado tem: fonte rastreável, score de qualidade (A/B/C/D), data de coleta e metodologia documentada. Dados com fonte única são marcados como "não verificados". Dados conflitantes são escalados para revisão humana. Nosso protocolo de correção é público.'
    },
    {
      question: 'Qual a diferença entre Sinal e Distrito/LAVCA/Crunchbase?',
      answer: 'Distrito é focado em enterprise. LAVCA atende apenas investidores. Crunchbase é global, em inglês, e com paywall. O Sinal é aberto, focado em builders técnicos (fundadores, CTOs, devs), com dados específicos de LATAM, metodologia publicada e comunidade ativa.'
    },
    {
      question: 'O que é um "Founding Member"?',
      answer: 'É uma turma limitada de primeiros apoiadores que financiam o laboratório desde o início. Além de acesso Pro, Founding Members votam no roadmap, participam de eventos exclusivos e têm seu nome na página de fundadores.'
    },
    {
      question: 'Vocês cobrem toda a América Latina?',
      answer: 'Começamos pelo Brasil, com cobertura já ativa em São Paulo, Florianópolis, Recife, Belo Horizonte, Curitiba, Porto Alegre, Campinas e Brasília. Nosso programa de Embaixadores Locais expande a cobertura continuamente. Expansão para mercados hispânicos está no roadmap.'
    },
    {
      question: 'Como posso contribuir?',
      answer: 'De várias formas: submeta dados sobre sua startup, participe do peer-review de análises, seja Embaixador da sua cidade, ou contribua com expertise no painel de validação. A inteligência do Sinal é construída pela comunidade.'
    },
    {
      question: 'E se eu encontrar um erro?',
      answer: 'Reporte em sinal.co/correcoes. Publicamos todas as correções com: texto original, texto corrigido, explicação e data. Nosso log de correções é público. Erros graves geram notificação a todos os assinantes.'
    }
  ];

  return (
    <Section>
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold mb-4">
          As respostas para as dúvidas mais frequentes.
        </h2>
      </div>

      <div className="max-w-3xl mx-auto space-y-4">
        {faqs.map((faq, index) => (
          <div key={index} className="border border-gray-200 rounded-lg">
            <button
              className="w-full px-6 py-4 flex justify-between items-center text-left hover:bg-gray-50 transition-colors"
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
            >
              <span className="font-bold pr-8">{faq.question}</span>
              <ChevronDown
                className={`w-5 h-5 flex-shrink-0 transition-transform ${
                  openIndex === index ? 'transform rotate-180' : ''
                }`}
              />
            </button>
            {openIndex === index && (
              <div className="px-6 pb-4">
                <p className="text-gray-700 leading-relaxed">{faq.answer}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </Section>
  );
}

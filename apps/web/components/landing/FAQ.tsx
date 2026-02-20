"use client";

import { useState } from "react";

const FAQ_ITEMS = [
  {
    question: "O que exatamente é o Sinal?",
    answer:
      "O Sinal é um laboratório aberto de pesquisa e inteligência de mercado sobre o ecossistema tech da América Latina. Produzimos um Briefing semanal, índices públicos, deep dives e dados verificáveis — tudo pesquisado por centenas de agentes de IA auditáveis e revisado por editores humanos.",
  },
  {
    question: "Como vocês usam inteligência artificial?",
    answer:
      "Nossos agentes de IA têm nomes, funções documentadas e metodologias publicadas. Eles coletam dados, cruzam fontes, checam fatos e detectam vieses. Mas nenhum conteúdo é publicado sem revisão humana. Você vê exatamente o que foi gerado por IA e o que foi editado por humanos.",
  },
  {
    question: "O Briefing é realmente gratuito?",
    answer:
      "Sim. O Briefing semanal é e sempre será gratuito. Acreditamos que inteligência de mercado é infraestrutura — não produto de luxo. A assinatura Pro financia pesquisa mais profunda, não tranca o acesso aos dados essenciais.",
  },
  {
    question: "Como vocês ganham dinheiro?",
    answer:
      "Três fontes: assinaturas Pro de leitores individuais, relatórios co-branded para empresas, e API de dados para plataformas corporativas. Não vendemos dados de leitores e não aceitamos conteúdo patrocinado disfarçado de editorial.",
  },
  {
    question: "Posso confiar nos dados?",
    answer:
      'Cada dado publicado tem: fonte rastreável, score de qualidade (A/B/C/D), data de coleta e metodologia documentada. Dados com fonte única são marcados como "não verificados". Dados conflitantes são escalados para revisão humana. Nosso protocolo de correção é público.',
  },
  {
    question: "Qual a diferença entre Sinal e Distrito/LAVCA/Crunchbase?",
    answer:
      "Distrito é focado em enterprise. LAVCA atende apenas investidores. Crunchbase é global, em inglês, e com paywall. O Sinal é aberto, focado em builders técnicos (fundadores, CTOs, devs), com dados específicos de LATAM, metodologia publicada e comunidade ativa.",
  },
  {
    question: "Vocês cobrem toda a América Latina?",
    answer:
      "Começamos pelo Brasil, com cobertura ativa nas principais cidades. Nosso programa de Embaixadores Locais expande a cobertura continuamente. Expansão para mercados hispânicos está no roadmap.",
  },
  {
    question: "E se eu encontrar um erro?",
    answer:
      "Reporte em sinal.co/correcoes. Publicamos todas as correções com: texto original, texto corrigido, explicação e data. Nosso log de correções é público. Erros graves geram notificação a todos os assinantes.",
  },
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  function toggle(index: number) {
    setOpenIndex(openIndex === index ? null : index);
  }

  return (
    <section id="faq" className="border-b border-[rgba(255,255,255,0.04)] py-section">
      <div className="mx-auto max-w-container px-6 md:px-10">
        {/* Section label */}
        <div className="mb-4 flex items-center gap-2.5">
          <span className="block h-px w-6 bg-signal" />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
            FAQ
          </span>
        </div>

        <h2 className="mb-12 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
          Perguntas frequentes.
        </h2>

        <div className="max-w-[720px]">
          {FAQ_ITEMS.map((item, index) => {
            const isOpen = openIndex === index;
            return (
              <div key={item.question} className="border-b border-[rgba(255,255,255,0.06)]">
                <button
                  onClick={() => toggle(index)}
                  className="flex w-full items-center justify-between gap-4 py-6 text-left font-body text-[16px] font-semibold text-sinal-white"
                  aria-expanded={isOpen}
                >
                  <span>{item.question}</span>
                  <span
                    className={`flex-shrink-0 font-mono text-[18px] font-light transition-transform duration-300 ${
                      isOpen ? "rotate-45 text-signal" : "text-ash"
                    }`}
                  >
                    +
                  </span>
                </button>
                <div
                  className={`overflow-hidden transition-all duration-400 ${
                    isOpen ? "max-h-[400px] pb-6" : "max-h-0"
                  }`}
                  style={{ transition: "max-height 0.4s ease, padding 0.3s" }}
                >
                  <p className="text-[15px] leading-[1.7] text-ash">{item.answer}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Section from "@/components/layout/Section";
import { AGENT_PERSONAS } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Sobre o Sinal",
  description: "Inteligência aberta para quem constrói na América Latina.",
  openGraph: {
    title: "Sobre o Sinal | Sinal",
    description: "Inteligência aberta para quem constrói na América Latina.",
    type: "website",
  },
};

const AGENT_COLOR_MAP: Record<string, string> = {
  "#E8FF59": "bg-agent-sintese",
  "#59FFB4": "bg-agent-radar",
  "#59B4FF": "bg-agent-codigo",
  "#FF8A59": "bg-agent-funding",
  "#C459FF": "bg-agent-mercado",
};

export default function SobrePage() {
  const agentes = Object.values(AGENT_PERSONAS);

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        {/* Header */}
        <Section label="SOBRE">
          <h1 className="font-display text-[clamp(32px,5vw,56px)] leading-tight text-sinal-white">
            O que é o Sinal.
          </h1>
          <p className="mt-6 max-w-[640px] text-[17px] leading-relaxed text-silver">
            O Sinal é uma plataforma de inteligência sobre o ecossistema tech da América Latina,
            construída para fundadores técnicos, CTOs e engenheiros seniores que precisam de dados
            confiáveis para tomar decisões.
          </p>
        </Section>

        {/* Mission */}
        <Section label="MISSÃO">
          <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
            Inteligência aberta para quem constrói.
          </h2>
          <div className="mt-8 max-w-[680px] space-y-6 text-[16px] leading-relaxed text-silver">
            <p>
              Toda semana, centenas de agentes especializados pesquisam, validam e sintetizam os
              dados mais relevantes sobre startups, investimentos, tecnologia e tendências na
              região. O resultado é entregue no formato de um briefing semanal — conciso, auditável
              e baseado em dados.
            </p>
            <p>
              O Sinal nasceu da frustração com a escassez de inteligência de qualidade sobre o
              ecossistema latinoamericano de tecnologia. A maioria das publicações existentes cobre
              o mercado de forma superficial, sem fontes verificáveis, sem metodologia transparente
              e sem foco no público técnico que de fato constrói as empresas da região.
            </p>
            <p>
              Nossa aposta é diferente: transparência radical, metodologia aberta e dados
              verificáveis. Cada informação publicada tem fonte, data de coleta e score de
              confiança. Você sabe exatamente de onde vem cada dado.
            </p>
          </div>
        </Section>

        {/* How it works */}
        <Section label="COMO FUNCIONA">
          <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
            Pesquisa automatizada, revisão humana.
          </h2>
          <p className="mt-6 max-w-[640px] text-[16px] leading-relaxed text-silver">
            O processo do Sinal combina escala computacional com julgamento editorial humano.
            Agentes de IA pesquisam e normalizam dados continuamente; um pipeline editorial filtra e
            prioriza; editores humanos revisam e aprovam antes de qualquer publicação.
          </p>
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-6">
              <span className="font-mono text-[11px] font-semibold uppercase tracking-[2px] text-signal">
                01
              </span>
              <h3 className="mt-3 font-body text-[15px] font-semibold text-sinal-white">
                Agentes pesquisam
              </h3>
              <p className="mt-2 text-[14px] leading-relaxed text-ash">
                Centenas de agentes monitoram fontes públicas verificáveis em tempo real — notícias,
                repositórios, bases de dados abertas e registros públicos.
              </p>
            </div>
            <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-6">
              <span className="font-mono text-[11px] font-semibold uppercase tracking-[2px] text-signal">
                02
              </span>
              <h3 className="mt-3 font-body text-[15px] font-semibold text-sinal-white">
                Pipeline filtra
              </h3>
              <p className="mt-2 text-[14px] leading-relaxed text-ash">
                Um pipeline editorial automatizado atribui scores de confiança, remove duplicatas e
                seleciona os itens mais relevantes para a audiência técnica.
              </p>
            </div>
            <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-6">
              <span className="font-mono text-[11px] font-semibold uppercase tracking-[2px] text-signal">
                03
              </span>
              <h3 className="mt-3 font-body text-[15px] font-semibold text-sinal-white">
                Humanos revisam
              </h3>
              <p className="mt-2 text-[14px] leading-relaxed text-ash">
                Editores revisam, contextualizam e aprovam cada item antes da publicação. Nenhum
                dado entra no briefing sem revisão humana.
              </p>
            </div>
          </div>
        </Section>

        {/* Team — Agent personas */}
        <Section label="OS AGENTES">
          <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
            Quem pesquisa o Sinal.
          </h2>
          <p className="mt-4 max-w-[560px] text-[16px] leading-relaxed text-silver">
            Cada agente é especializado em uma área do ecossistema tech LATAM e opera de forma
            contínua, com metodologia própria e auditável.
          </p>
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {agentes.map((agent) => {
              const bgClass = AGENT_COLOR_MAP[agent.color] ?? "bg-signal";
              return (
                <div
                  key={agent.agentCode}
                  className="flex items-start gap-4 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-5"
                >
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${bgClass}`}
                  >
                    <span className="font-mono text-[11px] font-semibold text-sinal-black">
                      {agent.agentCode.slice(0, 2)}
                    </span>
                  </div>
                  <div>
                    <p className="font-body text-[15px] font-semibold text-sinal-white">
                      {agent.name}
                    </p>
                    <p className="mt-0.5 font-mono text-[12px] text-ash">{agent.role}</p>
                    <p className="mt-2 text-[13px] leading-relaxed text-silver">
                      {agent.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </Section>
      </main>
      <Footer />
    </>
  );
}

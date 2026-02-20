import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Section from "@/components/layout/Section";

export const metadata: Metadata = {
  title: "Metodologia",
  description: "Como os agentes do Sinal pesquisam, validam e entregam inteligência.",
  openGraph: {
    title: "Metodologia | Sinal",
    description: "Como os agentes do Sinal pesquisam, validam e entregam inteligência.",
    type: "website",
  },
};

const PIPELINE_STEPS = [
  {
    number: "01",
    title: "Coleta",
    description:
      "Centenas de agentes coletam dados de fontes públicas verificáveis — notícias, repositórios de código, bases de dados abertas, registros de empresas e publicações especializadas.",
  },
  {
    number: "02",
    title: "Processamento",
    description:
      "Cada item é normalizado, categorizado e enriquecido. Valores monetários são convertidos para USD com taxa de câmbio registrada. Entidades (empresas, pessoas, investidores) são identificadas e vinculadas.",
  },
  {
    number: "03",
    title: "Validação",
    description:
      'Score de confiança atribuído com base no número de fontes independentes, consistência entre elas e proximidade com a data do evento. Dados financeiros exigem no mínimo 2 fontes para status "verificado".',
  },
  {
    number: "04",
    title: "Filtragem Editorial",
    description:
      "Pipeline editorial seleciona os itens mais relevantes para a audiência — fundadores técnicos, CTOs e engenheiros seniores da América Latina. Itens sem relevância técnica ou regional são descartados.",
  },
  {
    number: "05",
    title: "Síntese",
    description:
      "Agentes especializados redigem análises concisas e contextualizadas. Cada análise cita as fontes, registra o score de confiança e indica se o dado foi verificado por múltiplas fontes.",
  },
  {
    number: "06",
    title: "Revisão Humana",
    description:
      "Editores revisam, validam e aprovam antes da publicação. Nenhum conteúdo vai ao ar sem revisão humana. Correções são publicadas no Log de Correções com referência ao item original.",
  },
] as const;

const DQ_GRADES = [
  {
    grade: "A",
    label: "Verificado",
    description:
      "Multi-fonte verificado, recente (menos de 30 dias), com dados cruzados entre fontes independentes.",
    color: "text-agent-radar",
    borderColor: "border-agent-radar/30",
    bgColor: "bg-agent-radar/10",
  },
  {
    grade: "B",
    label: "Plausível",
    description:
      "Fonte única confiável, recente. Não contradiz outras informações públicas disponíveis.",
    color: "text-agent-sintese",
    borderColor: "border-agent-sintese/30",
    bgColor: "bg-agent-sintese/10",
  },
  {
    grade: "C",
    label: "Não verificado",
    description:
      "Fonte única sem corroboração ou dado com mais de 90 dias. Requer revisão humana antes do uso editorial.",
    color: "text-agent-funding",
    borderColor: "border-agent-funding/30",
    bgColor: "bg-agent-funding/10",
  },
  {
    grade: "D",
    label: "Contraditório",
    description:
      "Fontes divergentes ou dado que contradiz registros públicos. Escalado para editor antes de qualquer publicação.",
    color: "text-agent-mercado",
    borderColor: "border-agent-mercado/30",
    bgColor: "bg-agent-mercado/10",
  },
] as const;

export default function MetodologiaPage() {
  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        {/* Header */}
        <Section label="METODOLOGIA">
          <h1 className="font-display text-[clamp(32px,5vw,56px)] leading-tight text-sinal-white">
            Como funciona o Sinal.
          </h1>
          <p className="mt-6 max-w-[640px] text-[17px] leading-relaxed text-silver">
            Toda informação publicada no Sinal passa por um pipeline de 6 etapas — da coleta
            automatizada à revisão humana. Esta página documenta cada etapa de forma aberta e
            auditável.
          </p>
        </Section>

        {/* Pipeline — 6 steps */}
        <Section label="PIPELINE">
          <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
            6 etapas, da fonte ao briefing.
          </h2>
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {PIPELINE_STEPS.map((step) => (
              <div
                key={step.number}
                className="flex flex-col gap-3 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-6"
              >
                <span className="font-display text-[28px] leading-none text-signal">
                  {step.number}
                </span>
                <h3 className="font-body text-[15px] font-semibold text-sinal-white">
                  {step.title}
                </h3>
                <p className="text-[14px] leading-relaxed text-silver">{step.description}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* DQ Score */}
        <Section label="SCORE DE QUALIDADE">
          <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
            DQ Score — Data Quality.
          </h2>
          <p className="mt-4 max-w-[640px] text-[16px] leading-relaxed text-silver">
            Cada dado publicado carrega um DQ Score que sinaliza o nível de verificação. A escala
            vai de A (completamente verificado) a D (contraditório, requer investigação).
          </p>
          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {DQ_GRADES.map((item) => (
              <div
                key={item.grade}
                className={`flex items-start gap-5 rounded-xl border p-5 ${item.borderColor} ${item.bgColor}`}
              >
                <span className={`font-display text-[32px] leading-none ${item.color}`}>
                  {item.grade}
                </span>
                <div>
                  <p className={`font-body text-[15px] font-semibold ${item.color}`}>
                    {item.label}
                  </p>
                  <p className="mt-1.5 text-[14px] leading-relaxed text-silver">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Transparency */}
        <Section label="TRANSPARÊNCIA">
          <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
            Cada dado, rastreável até a fonte.
          </h2>
          <div className="mt-8 max-w-[680px] space-y-6 text-[16px] leading-relaxed text-silver">
            <p>
              Cada dado publicado inclui fonte, data de coleta e score de confiança. Não há
              &ldquo;dados de mercado&rdquo; sem origem ou &ldquo;fontes próximo ao setor&rdquo; sem
              identificação — se não é verificável, não é publicado.
            </p>
            <p>
              Quando erramos, corrigimos publicamente. O Log de Correções registra cada alteração
              com referência ao item original, data da correção e descrição do que mudou.
              Transparência total, inclusive nos erros.
            </p>
            <p>
              O código dos agentes é aberto no GitHub. Qualquer pessoa pode auditar a metodologia,
              propor melhorias ou identificar vieses no processo de coleta e curadoria.
            </p>
          </div>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <a
              href="https://github.com/fabianocruz/sinal-lab"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.12)] px-5 py-2.5 font-mono text-[13px] text-silver transition-colors hover:border-[rgba(255,255,255,0.24)] hover:text-sinal-white"
            >
              Ver código no GitHub
            </a>
            <a
              href="#"
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.12)] px-5 py-2.5 font-mono text-[13px] text-silver transition-colors hover:border-[rgba(255,255,255,0.24)] hover:text-sinal-white"
            >
              Log de Correções
            </a>
          </div>
        </Section>
      </main>
      <Footer />
    </>
  );
}

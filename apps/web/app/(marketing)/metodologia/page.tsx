import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Section from "@/components/layout/Section";

export const metadata: Metadata = {
  title: "Metodologia",
  description: "Como os agentes do Sinal pesquisam, validam e entregam inteligencia.",
  openGraph: {
    title: "Metodologia | Sinal",
    description: "Como os agentes do Sinal pesquisam, validam e entregam inteligencia.",
    type: "website",
  },
};

const PIPELINE_STEPS = [
  {
    number: "01",
    title: "Coleta",
    description:
      "Centenas de agentes coletam dados de fontes publicas verificaveis — noticias, repositorios de codigo, bases de dados abertas, registros de empresas e publicacoes especializadas.",
  },
  {
    number: "02",
    title: "Processamento",
    description:
      "Cada item e normalizado, categorizado e enriquecido. Valores monetarios sao convertidos para USD com taxa de cambio registrada. Entidades (empresas, pessoas, investidores) sao identificadas e vinculadas.",
  },
  {
    number: "03",
    title: "Validacao",
    description:
      'Score de confianca atribuido com base no numero de fontes independentes, consistencia entre elas e proximidade com a data do evento. Dados financeiros exigem no minimo 2 fontes para status "verificado".',
  },
  {
    number: "04",
    title: "Filtragem Editorial",
    description:
      "Pipeline editorial seleciona os itens mais relevantes para a audiencia — fundadores tecnicos, CTOs e engenheiros seniores da America Latina. Itens sem relevancia tecnica ou regional sao descartados.",
  },
  {
    number: "05",
    title: "Sintese",
    description:
      "Agentes especializados redigem analises concisas e contextualizadas. Cada analise cita as fontes, registra o score de confianca e indica se o dado foi verificado por multiplas fontes.",
  },
  {
    number: "06",
    title: "Revisao Humana",
    description:
      "Editores revisam, validam e aprovam antes da publicacao. Nenhum conteudo vai ao ar sem revisao humana. Correcoes sao publicadas no Log de Correcoes com referencia ao item original.",
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
    label: "Plausivel",
    description:
      "Fonte unica confiavel, recente. Nao contradiz outras informacoes publicas disponiveis.",
    color: "text-agent-sintese",
    borderColor: "border-agent-sintese/30",
    bgColor: "bg-agent-sintese/10",
  },
  {
    grade: "C",
    label: "Nao verificado",
    description:
      "Fonte unica sem corroboracao ou dado com mais de 90 dias. Requer revisao humana antes do uso editorial.",
    color: "text-agent-funding",
    borderColor: "border-agent-funding/30",
    bgColor: "bg-agent-funding/10",
  },
  {
    grade: "D",
    label: "Contradatorio",
    description:
      "Fontes divergentes ou dado que contradiz registros publicos. Escalado para editor antes de qualquer publicacao.",
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
            Toda informacao publicada no Sinal passa por um pipeline de 6 etapas — da coleta
            automatizada a revisao humana. Esta pagina documenta cada etapa de forma aberta e
            auditavel.
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
            Cada dado publicado carrega um DQ Score que sinaliza o nivel de verificacao. A escala
            vai de A (completamente verificado) a D (contradatorio, requer investigacao).
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
        <Section label="TRANSPARENCIA">
          <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
            Cada dado, rastreavel ate a fonte.
          </h2>
          <div className="mt-8 max-w-[680px] space-y-6 text-[16px] leading-relaxed text-silver">
            <p>
              Cada dado publicado inclui fonte, data de coleta e score de confianca. Nao ha
              &ldquo;dados de mercado&rdquo; sem origem ou &ldquo;fontes proximo ao setor&rdquo; sem
              identificacao — se nao e verificavel, nao e publicado.
            </p>
            <p>
              Quando erramos, corrigimos publicamente. O Log de Correcoes registra cada alteracao
              com referencia ao item original, data da correcao e descricao do que mudou.
              Transparencia total, inclusive nos erros.
            </p>
            <p>
              O codigo dos agentes e aberto no GitHub. Qualquer pessoa pode auditar a metodologia,
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
              Ver codigo no GitHub
            </a>
            <a
              href="#"
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.12)] px-5 py-2.5 font-mono text-[13px] text-silver transition-colors hover:border-[rgba(255,255,255,0.24)] hover:text-sinal-white"
            >
              Log de Correcoes
            </a>
          </div>
        </Section>
      </main>
      <Footer />
    </>
  );
}

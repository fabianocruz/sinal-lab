import type { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import LegalPageLayout from "@/components/legal/LegalPageLayout";
import LegalSection from "@/components/legal/LegalSection";

export const metadata: Metadata = {
  title: "Termos de Uso",
  description:
    "Termos de uso da plataforma Sinal — condições, propriedade intelectual e responsabilidades.",
  openGraph: {
    title: "Termos de Uso | Sinal",
    description:
      "Termos de uso da plataforma Sinal — condições, propriedade intelectual e responsabilidades.",
    type: "website",
  },
};

const LAST_UPDATED = "24 de fevereiro de 2026";
const COMPANY = "Sinal Tecnologia Ltda.";
const CNPJ = "59.864.556/0001-79";

const TOC = [
  "Definições",
  "Objeto",
  "Cadastro e Conta",
  "Planos e Pagamentos",
  "Propriedade Intelectual",
  "Conteúdo Gerado por IA",
  "Uso Aceitável",
  "Limitação de Responsabilidade",
  "Modificações",
  "Legislação e Foro",
];

const FOOTER_LINKS = [
  { label: "Privacidade (LGPD)", href: "/privacidade", color: "#C459FF" },
  { label: "Contato", href: "/contato" },
];

export default function TermosPage() {
  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <LegalPageLayout
          toc={TOC}
          sectionPrefix="s"
          accentColor="#E8FF59"
          footerLinks={FOOTER_LINKS}
        >
          {/* Hero */}
          <div className="mb-10">
            <div className="mb-3 font-mono text-[10px] uppercase tracking-[2px] text-signal">
              INSTITUCIONAL
            </div>
            <h1 className="mb-3.5 font-display text-4xl font-normal leading-tight text-sinal-white">
              Termos de Uso
            </h1>
            <p className="mb-4 max-w-[560px] text-[15px] leading-relaxed text-ash">
              Ao acessar ou utilizar a plataforma Sinal, você concorda com estes termos. Se não
              concorda, não utilize o serviço.
            </p>
            <div className="inline-flex items-center gap-2 rounded-md border border-sinal-slate bg-sinal-graphite px-3 py-1.5 font-mono text-[10px] text-[#4A4A56]">
              <span>v1.0</span>
              <span className="text-sinal-slate">&middot;</span>
              <span>{LAST_UPDATED}</span>
            </div>
          </div>

          <LegalSection id="s1" num="1" title="Definições">
            <p className="mb-3">
              <strong className="text-sinal-white">&ldquo;Sinal&rdquo;</strong> ou{" "}
              <strong className="text-sinal-white">&ldquo;Plataforma&rdquo;</strong>: refere-se ao
              site sinal.tech, newsletters, APIs, dashboards e todos os serviços digitais operados
              pela {COMPANY}, inscrita no CNPJ sob n.º {CNPJ}.
            </p>
            <p className="mb-3">
              <strong className="text-sinal-white">&ldquo;Usuário&rdquo;</strong>: pessoa física ou
              jurídica que acessa ou utiliza qualquer parte da Plataforma, gratuitamente ou mediante
              assinatura.
            </p>
            <p className="mb-3">
              <strong className="text-sinal-white">&ldquo;Conteúdo&rdquo;</strong>: textos, dados,
              análises, dashboards, market maps, rankings e quaisquer materiais produzidos e
              publicados pela Sinal, incluindo conteúdo gerado por AI agents.
            </p>
            <p className="mb-3">
              <strong className="text-sinal-white">&ldquo;AI Agents&rdquo;</strong>: sistemas
              automatizados de inteligência artificial que coletam, processam e sintetizam
              informações para produção de Conteúdo, conforme descrito na página de Metodologia.
            </p>
          </LegalSection>

          <LegalSection id="s2" num="2" title="Objeto">
            <p className="mb-3">
              A Sinal é uma plataforma de inteligência de mercado sobre AI, fintech e infraestrutura
              digital na América Latina. Fornecemos newsletters, análises, dados e ferramentas
              produzidos por AI agents auditáveis e validados por editores humanos.
            </p>
            <p className="mb-3">
              O Conteúdo tem finalidade exclusivamente informativa e educacional.{" "}
              <strong className="text-sinal-white">
                Não constitui recomendação de investimento, assessoria financeira, jurídica ou
                contábil.
              </strong>
            </p>
          </LegalSection>

          <LegalSection id="s3" num="3" title="Cadastro e Conta">
            <p className="mb-3">
              Para acessar determinados recursos (newsletter, dashboards, área Pro), é necessário
              criar uma conta fornecendo endereço de email válido. Você é responsável por manter a
              confidencialidade de suas credenciais.
            </p>
            <p className="mb-3">
              Ao se cadastrar, você declara ter 18 anos ou mais e capacidade legal para aceitar
              estes termos. Informações falsas podem resultar em suspensão de acesso.
            </p>
          </LegalSection>

          <LegalSection id="s4" num="4" title="Planos e Pagamentos">
            <p className="mb-3">
              <strong className="text-sinal-white">Plano Gratuito:</strong> inclui o Briefing
              Semanal, acesso ao Mapa de Startups e ao arquivo público. Não há cobrança.
            </p>
            <p className="mb-3">
              <strong className="text-sinal-white">Plano Pro:</strong> inclui Deep Dives completos,
              dashboards interativos, dados brutos e relatórios trimestrais. Valores e condições
              descritos na página de Preços.
            </p>
            <p className="mb-3">
              Assinaturas Pro são cobradas mensalmente ou anualmente, conforme escolha do Usuário. O
              cancelamento pode ser feito a qualquer momento; o acesso Pro permanece ativo até o fim
              do período pago. Não há reembolso proporcional.
            </p>
          </LegalSection>

          <LegalSection id="s5" num="5" title="Propriedade Intelectual">
            <p className="mb-3">
              Todo o Conteúdo publicado na Plataforma é de propriedade da {COMPANY} ou de seus
              licenciadores, protegido pelas leis brasileiras de direitos autorais (Lei 9.610/98) e
              propriedade industrial.
            </p>
            <p className="mb-3">
              <strong className="text-sinal-white">Uso permitido:</strong> você pode citar trechos
              do Conteúdo com atribuição clara à Sinal (incluindo link para o conteúdo original).
              Gráficos e tabelas podem ser reproduzidos com crédito &ldquo;Fonte: Sinal
              (sinal.tech)&rdquo;.
            </p>
            <p className="mb-3">
              <strong className="text-sinal-white">Uso proibido:</strong> reprodução integral de
              artigos, redistribuição comercial do Conteúdo, remoção de atribuição, uso do Conteúdo
              para treinar modelos de IA sem autorização expressa.
            </p>
          </LegalSection>

          <LegalSection id="s6" num="6" title="Conteúdo Gerado por IA">
            <p className="mb-3">
              Parte significativa do Conteúdo da Sinal é produzida por AI agents. Todo conteúdo
              gerado por IA passa por pipeline de validação automatizada e revisão humana editorial
              antes de publicação.
            </p>
            <p className="mb-3">
              Apesar dos nossos esforços de validação, conteúdo gerado por IA pode conter
              imprecisões. A Sinal publica um score de confiança (DQ Score) em cada peça de conteúdo
              e mantém um Log de Correções público para transparência.
            </p>
            <p className="mb-3">
              <strong className="text-sinal-white">
                A Sinal não se responsabiliza por decisões tomadas com base exclusiva em conteúdo
                gerado por IA.
              </strong>{" "}
              Recomendamos sempre verificar informações críticas em fontes primárias.
            </p>
          </LegalSection>

          <LegalSection id="s7" num="7" title="Uso Aceitável">
            <p className="mb-3">Ao utilizar a Plataforma, você concorda em não:</p>
            <ul className="mb-3.5 space-y-1.5 pl-5">
              <li className="pl-1">
                Realizar scraping, crawling ou coleta automatizada de Conteúdo sem autorização
              </li>
              <li className="pl-1">Redistribuir Conteúdo Pro para não-assinantes</li>
              <li className="pl-1">
                Utilizar a Plataforma para atividades ilegais ou fraudulentas
              </li>
              <li className="pl-1">Tentar acessar sistemas, redes ou dados não autorizados</li>
              <li className="pl-1">Criar contas falsas ou múltiplas para burlar limites de uso</li>
              <li className="pl-1">
                Usar o Conteúdo para treinar modelos de IA, machine learning ou sistemas
                automatizados sem autorização expressa
              </li>
            </ul>
            <p className="mb-3">
              A Sinal reserva-se o direito de suspender ou encerrar contas que violem estes termos,
              sem aviso prévio.
            </p>
          </LegalSection>

          <LegalSection id="s8" num="8" title="Limitação de Responsabilidade">
            <p className="mb-3">
              O Conteúdo é fornecido &ldquo;como está&rdquo; (as is). A Sinal não garante que as
              informações sejam completas, atualizadas ou livres de erro em todos os momentos.
            </p>
            <p className="mb-3">
              Em nenhuma circunstância a {COMPANY} será responsável por danos diretos, indiretos,
              incidentais, consequenciais ou punitivos decorrentes do uso ou da impossibilidade de
              uso da Plataforma ou do Conteúdo.
            </p>
            <p className="mb-3">
              A responsabilidade total da Sinal, quando cabível, limita-se ao valor pago pelo
              Usuário nos últimos 12 meses de assinatura.
            </p>
          </LegalSection>

          <LegalSection id="s9" num="9" title="Modificações">
            <p className="mb-3">
              A Sinal pode alterar estes Termos a qualquer momento. Alterações relevantes serão
              comunicadas por email e/ou notificação na Plataforma com antecedência mínima de 15
              dias.
            </p>
            <p className="mb-3">
              O uso continuado da Plataforma após a entrada em vigor das alterações constitui
              aceitação dos novos termos. Versões anteriores ficam disponíveis no histórico desta
              página.
            </p>
          </LegalSection>

          <LegalSection id="s10" num="10" title="Legislação e Foro">
            <p className="mb-3">
              Estes Termos são regidos pelas leis da República Federativa do Brasil.
            </p>
            <p className="mb-3">
              Fica eleito o foro da Comarca do Rio de Janeiro, Estado do Rio de Janeiro, para
              dirimir quaisquer controvérsias decorrentes destes Termos, com renúncia a qualquer
              outro, por mais privilegiado que seja.
            </p>
          </LegalSection>

          {/* Footer CTA */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
            <p className="text-[13px] text-silver">Dúvidas sobre estes termos?</p>
            <Link
              href="/contato"
              className="rounded-lg border border-signal px-4.5 py-2 font-mono text-xs font-semibold text-signal no-underline transition-colors hover:bg-signal hover:text-sinal-black"
            >
              Fale conosco &rarr;
            </Link>
          </div>
        </LegalPageLayout>
      </main>
      <Footer />
    </>
  );
}

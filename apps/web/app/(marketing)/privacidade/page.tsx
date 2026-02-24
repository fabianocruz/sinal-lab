import type { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import LegalPageLayout from "@/components/legal/LegalPageLayout";
import LegalSection from "@/components/legal/LegalSection";
import LegalTable from "@/components/legal/LegalTable";

export const metadata: Metadata = {
  title: "Política de Privacidade",
  description: "Como a Sinal trata seus dados pessoais — transparência, LGPD e seus direitos.",
  openGraph: {
    title: "Política de Privacidade | Sinal",
    description: "Como a Sinal trata seus dados pessoais — transparência, LGPD e seus direitos.",
    type: "website",
  },
};

const LAST_UPDATED = "24 de fevereiro de 2026";
const COMPANY = "Sinal Tecnologia Ltda.";
const CNPJ = "59.864.556/0001-79";
const EMAIL_DPO = "privacidade@sinal.tech";

const TOC = [
  "Controlador",
  "Dados que Coletamos",
  "Finalidade e Base Legal",
  "Cookies",
  "Compartilhamento",
  "Armazenamento e Segurança",
  "Retenção",
  "Seus Direitos (LGPD)",
  "Dados de Menores",
  "Transferência Internacional",
  "Encarregado (DPO)",
  "Alterações",
];

const FOOTER_LINKS = [
  { label: "Termos de Uso", href: "/termos", color: "#E8FF59" },
  { label: "Contato", href: "/contato" },
];

export default function PrivacidadePage() {
  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <LegalPageLayout
          toc={TOC}
          sectionPrefix="p"
          accentColor="#C459FF"
          footerLinks={FOOTER_LINKS}
        >
          {/* Hero */}
          <div className="mb-8">
            <div className="mb-3 font-mono text-[10px] uppercase tracking-[2px] text-agent-mercado">
              PRIVACIDADE & LGPD
            </div>
            <h1 className="mb-3.5 font-display text-4xl font-normal leading-tight text-sinal-white">
              Política de Privacidade
            </h1>
            <p className="mb-4 max-w-[560px] text-[15px] leading-relaxed text-ash">
              A Sinal trata seus dados com o mesmo rigor que aplica aos dados que publica:
              transparência, fonte rastreável e mínimo necessário.
            </p>
            <div className="inline-flex items-center gap-2 rounded-md border border-sinal-slate bg-sinal-graphite px-3 py-1.5 font-mono text-[10px] text-[#4A4A56]">
              <span>v1.0</span>
              <span className="text-sinal-slate">&middot;</span>
              <span>{LAST_UPDATED}</span>
            </div>
          </div>

          {/* Key commitments */}
          <div className="mb-10 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {[
              {
                icon: "\u2713",
                text: "Não vendemos seus dados",
                color: "text-agent-radar",
              },
              {
                icon: "\u2713",
                text: "Sem trackers de terceiros",
                color: "text-agent-codigo",
              },
              {
                icon: "\u2713",
                text: "Mínimo de dados coletados",
                color: "text-signal",
              },
              {
                icon: "\u2713",
                text: "Exclusão a qualquer momento",
                color: "text-agent-mercado",
              },
            ].map((item) => (
              <div
                key={item.text}
                className="flex items-center gap-2.5 rounded-xl border border-sinal-slate bg-sinal-graphite p-3.5"
              >
                <span className={`text-sm ${item.color}`}>{item.icon}</span>
                <span className="text-xs text-silver">{item.text}</span>
              </div>
            ))}
          </div>

          {/* Sections */}
          <LegalSection id="p1" num="1" title="Controlador">
            <p className="mb-3">
              O controlador dos dados pessoais tratados pela Plataforma é a {COMPANY}, inscrita no
              CNPJ sob n.º {CNPJ}, com sede no Rio de Janeiro, RJ.
            </p>
            <p className="mb-3">
              Para exercer seus direitos ou tirar dúvidas sobre esta política, entre em contato com
              nosso Encarregado de Proteção de Dados (DPO) pelo email{" "}
              <a href={`mailto:${EMAIL_DPO}`} className="text-signal hover:underline">
                {EMAIL_DPO}
              </a>
              .
            </p>
          </LegalSection>

          <LegalSection id="p2" num="2" title="Dados que Coletamos">
            <p className="mb-3">
              Coletamos o mínimo de dados necessários para operar a Plataforma:
            </p>
            <LegalTable
              headers={["Dado", "Quando", "Obrigatório"]}
              rows={[
                ["Email", "Cadastro na newsletter", "Sim"],
                ["Nome", "Cadastro (opcional)", "Não"],
                ["Empresa / Cargo", "Cadastro Pro (opcional)", "Não"],
                ["Dados de pagamento", "Assinatura Pro", "Sim (Pro)"],
                ["IP e user agent", "Acesso ao site", "Automático"],
                ["Dados de navegação", "Uso da Plataforma", "Automático"],
              ]}
            />
            <p className="mb-3">
              <strong className="text-sinal-white">Não coletamos</strong> dados sensíveis (origem
              racial, convicção religiosa, dados de saúde, biometria, orientação sexual) conforme
              definidos no Art. 5.º, II da LGPD.
            </p>
          </LegalSection>

          <LegalSection id="p3" num="3" title="Finalidade e Base Legal">
            <p className="mb-3">
              Cada tratamento de dados tem finalidade específica e base legal definida conforme a
              Lei 13.709/2018:
            </p>
            <LegalTable
              headers={["Finalidade", "Base Legal", "Dados"]}
              rows={[
                ["Envio da newsletter", "Consentimento (Art. 7.º, I)", "Email"],
                ["Gestão da conta", "Execução de contrato (Art. 7.º, V)", "Email, nome"],
                [
                  "Cobrança e faturamento",
                  "Execução de contrato (Art. 7.º, V)",
                  "Dados de pagamento",
                ],
                [
                  "Segurança e prevenção a fraudes",
                  "Interesse legítimo (Art. 7.º, IX)",
                  "IP, user agent",
                ],
                [
                  "Melhoria da Plataforma",
                  "Interesse legítimo (Art. 7.º, IX)",
                  "Dados de navegação",
                ],
                ["Comunicações de marketing", "Consentimento (Art. 7.º, I)", "Email"],
              ]}
            />
            <p className="mb-3">
              Não tratamos dados para finalidades incompatíveis com as listadas acima. Se houver
              nova necessidade, solicitaremos seu consentimento.
            </p>
          </LegalSection>

          <LegalSection id="p4" num="4" title="Cookies">
            <p className="mb-3">
              Utilizamos cookies estritamente necessários para o funcionamento da Plataforma e
              cookies analíticos para compreender como nosso conteúdo é utilizado.
            </p>
            <LegalTable
              headers={["Cookie", "Tipo", "Duração", "Finalidade"]}
              rows={[
                ["Sessão", "Necessário", "Sessão", "Manter login ativo"],
                ["Preferências", "Funcional", "1 ano", "Idioma, tema, filtros"],
                ["Analytics", "Analítico", "1 ano", "Métricas de uso agregadas"],
              ]}
            />
            <p className="mb-3">
              <strong className="text-sinal-white">Não utilizamos</strong> cookies de publicidade,
              remarketing ou tracking de terceiros (Google Ads, Facebook Pixel, etc.).
            </p>
            <p className="mb-3">
              Você pode configurar seu navegador para recusar cookies. Isso pode limitar algumas
              funcionalidades da Plataforma.
            </p>
          </LegalSection>

          <LegalSection id="p5" num="5" title="Compartilhamento">
            <p className="mb-3">
              <strong className="text-sinal-white">
                Não vendemos, alugamos ou compartilhamos comercialmente seus dados pessoais.
              </strong>{" "}
              Compartilhamos dados apenas quando estritamente necessário para operar o serviço:
            </p>
            <LegalTable
              headers={["Processador", "Dados", "Finalidade", "País"]}
              rows={[
                ["Resend (email)", "Email", "Envio da newsletter", "EUA"],
                ["Stripe (pagamentos)", "Dados de pagamento", "Cobrança", "EUA"],
                ["Vercel (hosting)", "IP, user agent", "Infraestrutura", "EUA"],
              ]}
            />
            <p className="mb-3">
              Todos os processadores operam sob contratos que exigem conformidade com padrões de
              proteção de dados equivalentes à LGPD.
            </p>
          </LegalSection>

          <LegalSection id="p6" num="6" title="Armazenamento e Segurança">
            <p className="mb-3">
              Seus dados são armazenados em infraestrutura cloud com as seguintes medidas:
            </p>
            <ul className="mb-3.5 space-y-1.5 pl-5">
              <li className="pl-1">Criptografia em trânsito (TLS 1.3) e em repouso (AES-256)</li>
              <li className="pl-1">Autenticação de dois fatores para acesso administrativo</li>
              <li className="pl-1">Backups automatizados com retenção controlada</li>
              <li className="pl-1">Monitoramento de acesso e logs de auditoria</li>
              <li className="pl-1">Princípio do menor privilégio para acesso a dados</li>
            </ul>
          </LegalSection>

          <LegalSection id="p7" num="7" title="Retenção">
            <p className="mb-3">
              Retemos seus dados apenas pelo tempo necessário para cada finalidade:
            </p>
            <LegalTable
              headers={["Dado", "Retenção", "Após encerramento"]}
              rows={[
                ["Email (newsletter)", "Até cancelamento da inscrição", "Exclusão em 30 dias"],
                ["Conta e perfil", "Enquanto conta ativa", "Exclusão em 30 dias após solicitação"],
                ["Dados de pagamento", "5 anos (obrigação fiscal)", "Exclusão automática"],
                ["Logs de acesso", "6 meses (Marco Civil da Internet)", "Exclusão automática"],
              ]}
            />
          </LegalSection>

          <LegalSection id="p8" num="8" title="Seus Direitos (LGPD)">
            <p className="mb-3">
              Conforme os Arts. 17 e 18 da Lei 13.709/2018 (LGPD), você tem direito a:
            </p>
            <ul className="mb-3.5 space-y-1.5 pl-5">
              <li className="pl-1">Confirmação da existência de tratamento de dados</li>
              <li className="pl-1">Acesso aos dados pessoais que tratamos sobre você</li>
              <li className="pl-1">Correção de dados incompletos, inexatos ou desatualizados</li>
              <li className="pl-1">
                Anonimização, bloqueio ou eliminação de dados desnecessários ou excessivos
              </li>
              <li className="pl-1">Portabilidade dos dados a outro fornecedor de serviço</li>
              <li className="pl-1">Eliminação dos dados tratados com base em consentimento</li>
              <li className="pl-1">Informação sobre compartilhamento de dados com terceiros</li>
              <li className="pl-1">
                Informação sobre a possibilidade de não fornecer consentimento e suas consequências
              </li>
              <li className="pl-1">Revogação do consentimento a qualquer momento</li>
            </ul>
            <p className="mb-3">
              Para exercer qualquer desses direitos, envie email para{" "}
              <a href={`mailto:${EMAIL_DPO}`} className="text-signal hover:underline">
                {EMAIL_DPO}
              </a>{" "}
              com o assunto &ldquo;Requisição LGPD&rdquo;, ou use o formulário de{" "}
              <Link href="/contato" className="text-signal hover:underline">
                Contato
              </Link>{" "}
              selecionando &ldquo;Requisição LGPD&rdquo;.
            </p>
            <p className="mb-3">
              Responderemos em até <strong className="text-sinal-white">15 dias</strong>, conforme
              Art. 18, &sect;5.º da LGPD.
            </p>
            <p className="mb-3">
              Se não estiver satisfeito com nossa resposta, você pode apresentar reclamação à
              Autoridade Nacional de Proteção de Dados (ANPD) pelo site{" "}
              <a
                href="https://www.gov.br/anpd"
                target="_blank"
                rel="noopener noreferrer"
                className="text-signal hover:underline"
              >
                gov.br/anpd
              </a>
              .
            </p>
          </LegalSection>

          <LegalSection id="p9" num="9" title="Dados de Menores">
            <p className="mb-3">
              A Plataforma não é direcionada a menores de 18 anos. Não coletamos intencionalmente
              dados de menores. Se tomarmos conhecimento de que dados de menores foram coletados
              inadvertidamente, procederemos à exclusão imediata.
            </p>
          </LegalSection>

          <LegalSection id="p10" num="10" title="Transferência Internacional">
            <p className="mb-3">
              Alguns dos nossos processadores de dados (Resend, Stripe, Vercel) operam nos Estados
              Unidos. Essas transferências são realizadas com base no Art. 33 da LGPD, com
              salvaguardas contratuais que garantem nível de proteção equivalente ao da legislação
              brasileira.
            </p>
          </LegalSection>

          <LegalSection id="p11" num="11" title="Encarregado (DPO)">
            <p className="mb-3">
              O Encarregado pelo Tratamento de Dados Pessoais (Data Protection Officer) da Sinal
              pode ser contatado pelo email{" "}
              <a href={`mailto:${EMAIL_DPO}`} className="text-signal hover:underline">
                {EMAIL_DPO}
              </a>
              .
            </p>
            <p className="mb-3">
              O Encarregado é responsável por aceitar reclamações e comunicações dos titulares,
              prestar esclarecimentos e adotar providências, bem como receber comunicações da ANPD e
              adotar as medidas cabíveis, conforme Art. 41 da LGPD.
            </p>
          </LegalSection>

          <LegalSection id="p12" num="12" title="Alterações">
            <p className="mb-3">
              Esta Política de Privacidade pode ser atualizada periodicamente. Alterações relevantes
              serão comunicadas por email e/ou notificação na Plataforma com antecedência mínima de
              15 dias.
            </p>
            <p className="mb-3">
              O histórico de versões anteriores desta política está disponível mediante solicitação
              a{" "}
              <a href={`mailto:${EMAIL_DPO}`} className="text-signal hover:underline">
                {EMAIL_DPO}
              </a>
              .
            </p>
          </LegalSection>

          {/* DPO contact card */}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-agent-mercado/30 bg-agent-mercado/10 p-6">
            <div>
              <div className="mb-1.5 flex items-center gap-2">
                <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-agent-radar" />
                <span className="font-mono text-[9px] uppercase tracking-[1.5px] text-agent-mercado">
                  ENCARREGADO DE PROTEÇÃO DE DADOS
                </span>
              </div>
              <p className="text-sm text-silver">
                Para exercer seus direitos, entre em contato com nosso DPO.
              </p>
            </div>
            <a
              href={`mailto:${EMAIL_DPO}`}
              className="rounded-lg bg-agent-mercado px-5 py-2.5 font-mono text-xs font-semibold text-sinal-black no-underline transition-opacity hover:opacity-90"
            >
              {EMAIL_DPO} &rarr;
            </a>
          </div>

          {/* Bottom info */}
          <div className="mt-10 flex flex-wrap items-center justify-between border-t border-sinal-slate pt-6">
            <div className="font-mono text-[10px] text-[#4A4A56]">
              {COMPANY} &middot; CNPJ {CNPJ} &middot; Rio de Janeiro, RJ
            </div>
            <div className="flex gap-4">
              <Link href="/termos" className="text-xs text-ash no-underline hover:text-sinal-white">
                Termos de Uso
              </Link>
              <Link
                href="/contato"
                className="text-xs text-ash no-underline hover:text-sinal-white"
              >
                Contato
              </Link>
            </div>
          </div>
        </LegalPageLayout>
      </main>
      <Footer />
    </>
  );
}

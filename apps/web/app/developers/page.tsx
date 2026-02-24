import type { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Section from "@/components/layout/Section";
import ApiAccessForm from "@/components/developers/ApiAccessForm";
import DocsSidebar from "@/components/developers/DocsSidebar";
import EndpointBlock from "@/components/developers/EndpointBlock";
import { API_GROUPS, ERROR_CODES } from "@/lib/api-docs";

export const metadata: Metadata = {
  title: "Documentação da API | Sinal",
  description:
    "Documentação completa da API REST — empresas, conteúdo editorial, AI agents e investimentos do ecossistema tech LATAM.",
  openGraph: {
    title: "Documentação da API | Sinal",
    description:
      "Documentação completa da API REST — empresas, conteúdo editorial, AI agents e investimentos do ecossistema tech LATAM.",
    type: "website",
  },
};

export default function DevelopersPage() {
  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        {/* ── Hero ── */}
        <Section>
          <div className="py-8 md:py-16">
            <span className="font-mono text-[11px] font-semibold uppercase tracking-[2px] text-signal">
              API de Dados
            </span>
            <h1 className="mt-4 font-display text-[clamp(32px,5vw,56px)] leading-tight text-sinal-white">
              Dados LATAM Tech
              <br />
              via API REST.
            </h1>
            <p className="mt-6 max-w-[560px] text-[17px] leading-relaxed text-silver">
              Documentação completa dos endpoints REST para acessar startups, investimentos,
              conteúdo editorial e métricas de AI agents do ecossistema tech da América Latina.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="#solicitar-acesso"
                className="inline-block rounded-lg bg-signal px-7 py-3.5 font-body text-[15px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim"
              >
                Solicitar Acesso
              </Link>
              <Link
                href="#visao-geral"
                className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.12)] px-7 py-3.5 font-body text-[15px] text-silver transition-colors hover:border-[rgba(255,255,255,0.24)] hover:text-sinal-white"
              >
                Ver Endpoints
              </Link>
            </div>
          </div>
        </Section>

        {/* ── Documentation body (sidebar + content) ── */}
        <div className="mx-auto max-w-container px-6 py-section md:px-10">
          <div className="lg:grid lg:grid-cols-[180px_1fr] lg:gap-10">
            <DocsSidebar />

            <div className="space-y-16 md:space-y-20">
              {/* ── Visao Geral ── */}
              <section id="visao-geral">
                <div className="mb-6 flex items-center gap-3">
                  <span className="block h-px w-6 bg-signal" />
                  <span className="font-mono text-[11px] font-semibold uppercase tracking-[2px] text-signal">
                    Visão Geral
                  </span>
                </div>
                <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
                  APIs disponíveis.
                </h2>
                <p className="mt-4 max-w-[560px] text-[16px] leading-relaxed text-silver">
                  Endpoints REST com paginação, filtros e respostas em JSON. Todos os dados incluem
                  proveniência e scores de confiança.
                </p>

                <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {API_GROUPS.map((group) => (
                    <a
                      key={group.id}
                      href={`#${group.id}`}
                      className="group rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-[rgba(255,255,255,0.12)]"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block h-2 w-2 rounded-full"
                          style={{ backgroundColor: group.color }}
                        />
                        <span className="font-body text-[15px] font-semibold text-sinal-white">
                          {group.name}
                        </span>
                        {group.comingSoon && (
                          <span className="ml-auto rounded bg-[rgba(255,255,255,0.06)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[1px] text-ash">
                            Em breve
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-[13px] leading-relaxed text-ash">
                        {group.description}
                      </p>
                      <span className="mt-3 inline-block font-mono text-[11px] text-silver group-hover:text-signal">
                        {group.fieldCount} &middot; {group.endpoints.length}{" "}
                        {group.endpoints.length === 1 ? "endpoint" : "endpoints"}
                      </span>
                    </a>
                  ))}
                </div>
              </section>

              {/* ── Autenticacao ── */}
              <section id="autenticacao">
                <div className="mb-6 flex items-center gap-3">
                  <span className="block h-px w-6 bg-signal" />
                  <span className="font-mono text-[11px] font-semibold uppercase tracking-[2px] text-signal">
                    Autenticação
                  </span>
                </div>
                <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
                  API Key via header.
                </h2>
                <p className="mt-4 max-w-[560px] text-[16px] leading-relaxed text-silver">
                  Todas as requisições precisam de uma API key válida enviada no header{" "}
                  <code className="rounded bg-sinal-slate px-1.5 py-0.5 font-mono text-[14px] text-signal">
                    Authorization
                  </code>
                  .
                </p>
                <div className="mt-6 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite">
                  <div className="border-b border-[rgba(255,255,255,0.04)] px-5 py-3">
                    <span className="font-mono text-[11px] text-ash">Header de autenticação</span>
                  </div>
                  <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-relaxed text-ash">
                    {`Authorization: Bearer YOUR_API_KEY`}
                  </pre>
                </div>
                <div className="mt-6 rounded-xl border border-[rgba(255,138,89,0.2)] bg-[rgba(255,138,89,0.04)] p-5">
                  <p className="text-[14px] leading-relaxed text-silver">
                    <span className="font-semibold text-[#FF8A59]">Sem API key?</span> Solicite
                    acesso pelo{" "}
                    <a
                      href="#solicitar-acesso"
                      className="text-signal underline underline-offset-2 hover:text-signal-dim"
                    >
                      formulário abaixo
                    </a>
                    . Nossa equipe responde em até 48 horas com sua chave e documentação.
                  </p>
                </div>
              </section>

              {/* ── Endpoint sections (Companies, Content, Agents) ── */}
              {API_GROUPS.filter((g) => !g.comingSoon).map((group) => (
                <section key={group.id} id={group.id}>
                  <div className="mb-6 flex items-center gap-3">
                    <span className="block h-px w-6" style={{ backgroundColor: group.color }} />
                    <span
                      className="font-mono text-[11px] font-semibold uppercase tracking-[2px]"
                      style={{ color: group.color }}
                    >
                      {group.label}
                    </span>
                  </div>
                  <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
                    {group.name}.
                  </h2>
                  <p className="mt-4 max-w-[560px] text-[14px] leading-relaxed text-silver">
                    {group.description}
                  </p>

                  <div className="mt-8 space-y-8">
                    {group.endpoints.map((ep) => (
                      <EndpointBlock key={ep.path} endpoint={ep} />
                    ))}
                  </div>
                </section>
              ))}

              {/* ── Investimentos (coming soon) ── */}
              {API_GROUPS.filter((g) => g.comingSoon).map((group) => (
                <section key={group.id} id={group.id}>
                  <div className="mb-6 flex items-center gap-3">
                    <span className="block h-px w-6" style={{ backgroundColor: group.color }} />
                    <span
                      className="font-mono text-[11px] font-semibold uppercase tracking-[2px]"
                      style={{ color: group.color }}
                    >
                      {group.label}
                    </span>
                    <span className="rounded bg-[rgba(255,255,255,0.06)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[1px] text-ash">
                      Em breve
                    </span>
                  </div>
                  <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
                    {group.name}.
                  </h2>
                  <p className="mt-4 max-w-[560px] text-[14px] leading-relaxed text-silver">
                    {group.description}
                  </p>

                  {/* Planned endpoint preview */}
                  {group.endpoints[0] && (
                    <div className="mt-6 flex items-center gap-3 rounded-lg border border-[rgba(255,255,255,0.04)] bg-sinal-black px-4 py-2.5">
                      <span className="rounded bg-[rgba(232,255,89,0.12)] px-2 py-0.5 font-mono text-[11px] font-semibold text-signal">
                        {group.endpoints[0].method}
                      </span>
                      <code className="font-mono text-[13px] text-sinal-white">
                        {group.endpoints[0].path}
                      </code>
                    </div>
                  )}

                  {/* Preview of planned fields */}
                  <div className="mt-8 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-5">
                    <h4 className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-[1.5px] text-ash">
                      Campos planejados
                    </h4>
                    <div className="space-y-2">
                      {group.endpoints[0]?.responseFields.map((field) => (
                        <div key={field.name} className="flex items-center gap-3">
                          <code className="font-mono text-[13px] text-sinal-white">
                            {field.name}
                          </code>
                          <span className="font-mono text-[11px] text-signal">{field.type}</span>
                          <span className="text-[12px] text-ash">{field.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              ))}

              {/* ── Paginacao e Filtros ── */}
              <section id="paginacao">
                <div className="mb-6 flex items-center gap-3">
                  <span className="block h-px w-6 bg-signal" />
                  <span className="font-mono text-[11px] font-semibold uppercase tracking-[2px] text-signal">
                    Paginação e Filtros
                  </span>
                </div>
                <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
                  Padrões compartilhados.
                </h2>
                <p className="mt-4 max-w-[560px] text-[16px] leading-relaxed text-silver">
                  Todos os endpoints de listagem seguem o mesmo envelope de paginação e aceitam os
                  parâmetros{" "}
                  <code className="rounded bg-sinal-slate px-1.5 py-0.5 font-mono text-[14px] text-signal">
                    limit
                  </code>{" "}
                  e{" "}
                  <code className="rounded bg-sinal-slate px-1.5 py-0.5 font-mono text-[14px] text-signal">
                    offset
                  </code>
                  .
                </p>

                <div className="mt-6 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite">
                  <div className="border-b border-[rgba(255,255,255,0.04)] px-5 py-3">
                    <span className="font-mono text-[11px] text-ash">Envelope de paginação</span>
                  </div>
                  <pre className="overflow-x-auto p-5 font-mono text-[12px] leading-relaxed text-ash">
                    {`{
  "items": [...],     // Array de objetos
  "total": 847,       // Total de registros (antes da paginação)
  "limit": 20,        // Tamanho da página (default: 20, max: 100)
  "offset": 0         // Deslocamento atual
}`}
                  </pre>
                </div>

                <div className="mt-6 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-5">
                  <h4 className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-[1.5px] text-ash">
                    Filtro de busca
                  </h4>
                  <p className="text-[14px] leading-relaxed text-silver">
                    O parâmetro{" "}
                    <code className="rounded bg-sinal-slate px-1.5 py-0.5 font-mono text-[14px] text-signal">
                      search
                    </code>{" "}
                    faz busca case-insensitive (LIKE) no campo principal do recurso (nome para
                    empresas, título para conteúdo).
                  </p>
                </div>
              </section>

              {/* ── Codigos de Erro ── */}
              <section id="erros">
                <div className="mb-6 flex items-center gap-3">
                  <span className="block h-px w-6 bg-signal" />
                  <span className="font-mono text-[11px] font-semibold uppercase tracking-[2px] text-signal">
                    Códigos de Erro
                  </span>
                </div>
                <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
                  Respostas de erro.
                </h2>
                <p className="mt-4 max-w-[560px] text-[16px] leading-relaxed text-silver">
                  Todas as respostas de erro seguem o formato padrão com o campo{" "}
                  <code className="rounded bg-sinal-slate px-1.5 py-0.5 font-mono text-[14px] text-signal">
                    detail
                  </code>
                  .
                </p>

                <div className="mt-6 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite">
                  <div className="border-b border-[rgba(255,255,255,0.04)] px-5 py-3">
                    <span className="font-mono text-[11px] text-ash">Formato de erro</span>
                  </div>
                  <pre className="overflow-x-auto p-5 font-mono text-[12px] leading-relaxed text-ash">
                    {`{
  "detail": "Company 'xyz' not found"
}`}
                  </pre>
                </div>

                <div className="mt-6 overflow-x-auto rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-[rgba(255,255,255,0.1)]">
                        <th className="px-5 py-3 font-mono text-[11px] uppercase tracking-[1px] text-ash">
                          Código
                        </th>
                        <th className="px-5 py-3 font-mono text-[11px] uppercase tracking-[1px] text-ash">
                          Nome
                        </th>
                        <th className="px-5 py-3 font-mono text-[11px] uppercase tracking-[1px] text-ash">
                          Descrição
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {ERROR_CODES.map((err) => (
                        <tr key={err.code} className="border-b border-[rgba(255,255,255,0.04)]">
                          <td className="px-5 py-3 font-mono text-[13px] text-signal">
                            {err.code}
                          </td>
                          <td className="px-5 py-3 font-mono text-[13px] text-sinal-white">
                            {err.name}
                          </td>
                          <td className="px-5 py-3 text-[13px] text-silver">{err.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </div>
        </div>

        {/* ── Solicitar Acesso ── */}
        <Section label="SOLICITAR ACESSO" id="solicitar-acesso">
          <h2 className="font-display text-[clamp(24px,4vw,40px)] leading-tight text-sinal-white">
            Solicite acesso a API.
          </h2>
          <p className="mt-4 max-w-[560px] text-[16px] leading-relaxed text-silver">
            Preencha o formulário abaixo. Nossa equipe analisa cada solicitação e responde em até 48
            horas com sua API Key e documentação.
          </p>
          <div className="mt-8 max-w-[640px]">
            <ApiAccessForm />
          </div>
        </Section>
      </main>
      <Footer />
    </>
  );
}

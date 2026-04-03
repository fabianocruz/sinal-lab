import type { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Log de Correções",
  description:
    "Registro público de todas as correções editoriais do Sinal. Transparência sobre erros, o que foi corrigido e por quê.",
};

const CORRECTIONS = [
  {
    date: "2026-03-30",
    edition: "Sinal Semanal #52",
    slug: "sinal-semanal-52",
    items: [
      {
        original:
          "Edição incluía item duplicado sobre R3 Bio (clones humanos sem cérebro) com análises de duas fontes separadas.",
        corrected:
          "Consolidado em um único item com análise unificada. Segundo item redundante removido.",
        reason:
          "Duplicação editorial: mesmo tema coberto por MIT Tech Review em dois artigos distintos que foram tratados como itens independentes pelo agente.",
      },
      {
        original: "Uber/Blacklane aparecia em dois itens separados (TechCrunch e Engadget).",
        corrected: "Consolidado em um único item com a fonte mais completa (TechCrunch).",
        reason:
          "Dedup cross-source não detectou cobertura duplicada do mesmo evento por fontes diferentes.",
      },
    ],
  },
];

export default function CorrecoesPage() {
  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-[720px] px-6 py-16 md:px-10">
          <h1 className="font-display text-[clamp(28px,4vw,40px)] leading-[1.15] text-sinal-white">
            Log de Correções
          </h1>
          <p className="mt-4 text-[16px] leading-relaxed text-silver">
            Registro público de todas as correções editoriais. Quando cometemos um erro, publicamos:
            o que estava errado, o que foi corrigido, e por quê. Erros graves geram notificação a
            todos os assinantes.
          </p>
          <p className="mt-3 text-[14px] text-ash">
            Encontrou um erro?{" "}
            <Link href="/contato" className="text-signal underline underline-offset-2">
              Reporte aqui
            </Link>
          </p>

          {CORRECTIONS.length === 0 ? (
            <div className="mt-12 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-8 text-center">
              <p className="text-[15px] text-silver">Nenhuma correção registrada ainda.</p>
            </div>
          ) : (
            <div className="mt-12 space-y-8">
              {CORRECTIONS.map((correction, i) => (
                <article
                  key={i}
                  className="rounded-xl border border-[rgba(255,255,255,0.04)] bg-sinal-graphite p-6"
                >
                  <div className="mb-4 flex flex-wrap items-center gap-3">
                    <span className="font-mono text-[11px] text-ash">{correction.date}</span>
                    <Link
                      href={`/newsletter/${correction.slug}`}
                      className="font-mono text-[12px] text-signal underline-offset-2 hover:underline"
                    >
                      {correction.edition}
                    </Link>
                  </div>

                  <div className="space-y-5">
                    {correction.items.map((item, j) => (
                      <div key={j} className="space-y-2">
                        <div className="flex items-start gap-2">
                          <span className="mt-1 shrink-0 font-mono text-[11px] text-red-400/80">
                            ANTES
                          </span>
                          <p className="text-[13px] leading-relaxed text-ash line-through decoration-red-400/30">
                            {item.original}
                          </p>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="mt-1 shrink-0 font-mono text-[11px] text-green-400/80">
                            DEPOIS
                          </span>
                          <p className="text-[13px] leading-relaxed text-silver">
                            {item.corrected}
                          </p>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="mt-1 shrink-0 font-mono text-[11px] text-ash/60">
                            POR QUE
                          </span>
                          <p className="text-[12px] leading-relaxed text-ash">{item.reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}

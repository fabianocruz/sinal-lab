import Link from "next/link";
import { fetchNewsletters } from "@/lib/api";
import { mapApiToNewsletter, type Newsletter } from "@/lib/newsletter";
import type { AgentKey } from "@/lib/constants";

const STRIP_GRADIENTS: Record<AgentKey, string> = {
  sintese: "linear-gradient(90deg, #E8FF59, #59FFB4)",
  radar: "linear-gradient(90deg, #59FFB4, #59B4FF)",
  codigo: "linear-gradient(90deg, #59B4FF, #C459FF)",
  funding: "linear-gradient(90deg, #FF8A59, #C459FF)",
  mercado: "linear-gradient(90deg, #C459FF, #E8FF59)",
};

const FALLBACK_EDITIONS = [
  {
    date: "10 FEV 2026",
    number: "Edição #47",
    title: "Healthtech LATAM: a vertical silenciosa que cresceu 340%",
    stripGradient: "linear-gradient(90deg, #E8FF59, #59FFB4)",
    href: "/newsletter",
  },
  {
    date: "03 FEV 2026",
    number: "Edição #46",
    title: "US$1.2B em deals no Q4: quem captou, de quem, e por quê",
    stripGradient: "linear-gradient(90deg, #59B4FF, #59FFB4)",
    href: "/newsletter",
  },
  {
    date: "27 JAN 2026",
    number: "Edição #45",
    title: "O mapa de calor do talento técnico na América Latina",
    stripGradient: "linear-gradient(90deg, #FF8A59, #C459FF)",
    href: "/newsletter",
  },
];

function newsletterToEdition(n: Newsletter) {
  return {
    date: n.date.toUpperCase(),
    number: n.edition > 0 ? `Edição #${n.edition}` : "Edição especial",
    title: n.title,
    stripGradient: STRIP_GRADIENTS[n.agent] ?? STRIP_GRADIENTS.sintese,
    href: `/newsletter/${n.slug}`,
  };
}

export default async function EditionsPreviews() {
  const data = await fetchNewsletters({ limit: 3 });
  const editions =
    data.items.length > 0
      ? data.items.map((item, i) => newsletterToEdition(mapApiToNewsletter(item, i)))
      : FALLBACK_EDITIONS;

  return (
    <section id="edicoes" className="border-b border-[rgba(255,255,255,0.04)] py-section">
      <div className="mx-auto max-w-container px-6 md:px-10">
        {/* Section label */}
        <div className="mb-4 flex items-center gap-2.5">
          <span className="block h-px w-6 bg-signal" />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
            Arquivo
          </span>
        </div>

        <h2 className="mb-5 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
          Veja o Briefing com
          <br />
          seus próprios olhos.
        </h2>
        <p className="mb-12 max-w-[600px] text-[17px] leading-[1.7] text-ash">
          Não pedimos que confie em nós. Pedimos que verifique. Aqui estão as últimas edições — com
          todas as fontes, metodologias e scores de confiança.
        </p>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 md:grid-cols-3">
          {editions.map((edition) => (
            <Link
              key={edition.number}
              href={edition.href}
              className="block overflow-hidden rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite transition-all duration-200 hover:-translate-y-0.5 hover:border-[rgba(255,255,255,0.1)]"
            >
              {/* Color strip */}
              <div className="h-[3px] w-full" style={{ background: edition.stripGradient }} />
              <div className="p-6">
                <div className="mb-3 font-mono text-[11px] tracking-[0.5px] text-ash">
                  {edition.date} · {edition.number}
                </div>
                <div className="mb-4 font-display text-[18px] leading-snug text-sinal-white">
                  {edition.title}
                </div>
                <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-signal">
                  Ler edição →
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

import Link from "next/link";

const FOOTER_COLUMNS = [
  {
    title: "Produto",
    links: [
      { label: "Briefing Semanal", href: "/newsletter" },
      { label: "Índices LATAM", href: "#" },
      { label: "Deep Dives", href: "#" },
      { label: "API de Dados", href: "/developers" },
      { label: "Para Empresas", href: "/#empresas" },
    ],
  },
  {
    title: "Comunidade",
    links: [
      { label: "Comunidade de Builders", href: "#" },
      { label: "Embaixadores Locais", href: "#" },
      { label: "Painel de Especialistas", href: "#" },
      { label: "Contribua com Dados", href: "#" },
    ],
  },
  {
    title: "Transparência",
    links: [
      { label: "Metodologia", href: "/#metodologia" },
      { label: "Fontes de Dados", href: "#" },
      { label: "Log de Correções", href: "#" },
      { label: "Dashboard de Viés", href: "#" },
      { label: "Changelog dos Agentes", href: "#" },
    ],
  },
  {
    title: "Institucional",
    links: [
      { label: "Sobre", href: "/sobre" },
      { label: "Manifesto", href: "/#manifesto" },
      { label: "Contato", href: "#" },
      { label: "Termos", href: "#" },
      { label: "Privacidade (LGPD)", href: "#" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="border-t border-[rgba(255,255,255,0.04)] bg-sinal-black">
      <div className="mx-auto max-w-container px-6 py-16 md:px-10">
        {/* Grid */}
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-[1.5fr_1fr_1fr_1fr_1fr]">
          {/* Brand column */}
          <div>
            <Link href="/" className="mb-4 flex items-center gap-1.5">
              <span className="font-display text-xl text-sinal-white">Sinal</span>
              <span className="inline-block h-[6px] w-[6px] rounded-full bg-signal shadow-[0_0_12px_rgba(232,255,89,0.4)]" />
            </Link>
            <p className="mt-3 max-w-[240px] text-[14px] leading-relaxed text-ash">
              Inteligência aberta para quem constrói.
            </p>
          </div>

          {/* Link columns */}
          {FOOTER_COLUMNS.map((col) => (
            <div key={col.title}>
              <h4 className="mb-4 font-mono text-[11px] font-semibold uppercase tracking-[2px] text-ash">
                {col.title}
              </h4>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-[14px] text-silver transition-colors hover:text-sinal-white"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-[rgba(255,255,255,0.04)] pt-8 sm:flex-row">
          <p className="font-mono text-[12px] text-ash">
            Transparência radical. Metodologia aberta. Dados verificáveis.
          </p>
          <div className="flex items-center gap-6">
            <a
              href="https://linkedin.com/company/sinal-lab"
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
            >
              LinkedIn
            </a>
            <a
              href="https://x.com/sinal_lab"
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
            >
              X
            </a>
            <a
              href="https://github.com/fabianocruz/sinal-lab"
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[12px] text-ash transition-colors hover:text-sinal-white"
            >
              GitHub
            </a>
          </div>
        </div>

        {/* Copyright */}
        <p className="mt-6 text-center font-mono text-[11px] text-ash/60">
          &copy; {new Date().getFullYear()} Sinal.lab. Todos os direitos reservados.
        </p>
      </div>
    </footer>
  );
}

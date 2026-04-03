import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Fontes de Dados",
  description:
    "150+ fontes alimentam os agentes de inteligência do Sinal. RSS, APIs, registros regulatórios e comunidades dev monitorados semanalmente.",
};

type Source = { name: string; url: string; type: string };

type AgentSources = {
  agent: string;
  color: string;
  description: string;
  categories: { label: string; sources: Source[] }[];
};

const AGENT_SOURCES: AgentSources[] = [
  {
    agent: "SINTESE",
    color: "#E8FF59",
    description: "Curadoria editorial cruzando todas as fontes",
    categories: [
      {
        label: "Tech Brasil",
        sources: [
          { name: "NeoFeed", url: "https://neofeed.com.br", type: "RSS" },
          { name: "Bloomberg Linea", url: "https://www.bloomberglinea.com.br", type: "RSS" },
          { name: "Mobile Time", url: "https://www.mobiletime.com.br", type: "RSS" },
          { name: "ABStartups", url: "https://abstartups.com.br", type: "RSS" },
          { name: "InfoMoney", url: "https://www.infomoney.com.br", type: "RSS" },
        ],
      },
      {
        label: "Tech Global",
        sources: [
          { name: "TechCrunch", url: "https://techcrunch.com", type: "RSS" },
          {
            name: "TechCrunch Latin America",
            url: "https://techcrunch.com/tag/latin-america",
            type: "RSS",
          },
          { name: "MIT Technology Review", url: "https://www.technologyreview.com", type: "RSS" },
          { name: "The Verge", url: "https://www.theverge.com", type: "RSS" },
          { name: "Ars Technica", url: "https://arstechnica.com", type: "RSS" },
          { name: "Wired", url: "https://www.wired.com", type: "RSS" },
          { name: "GeekWire", url: "https://www.geekwire.com", type: "RSS" },
          { name: "Engadget", url: "https://www.engadget.com", type: "RSS" },
          { name: "Fast Company", url: "https://www.fastcompany.com", type: "RSS" },
          { name: "CNBC Tech", url: "https://www.cnbc.com", type: "RSS" },
          { name: "Rest of World", url: "https://restofworld.org", type: "RSS" },
          { name: "LatamList", url: "https://latamlist.com", type: "RSS" },
          { name: "404 Media", url: "https://www.404media.co", type: "RSS" },
          { name: "Venture Beat AI", url: "https://venturebeat.com", type: "RSS" },
        ],
      },
      {
        label: "Newsletters e Blogs",
        sources: [
          { name: "Simon Willison", url: "https://simonwillison.net", type: "RSS" },
          { name: "TLDR Newsletter", url: "https://tldr.tech", type: "RSS" },
          { name: "ByteByteGo", url: "https://blog.bytebytego.com", type: "RSS" },
          {
            name: "Pragmatic Engineer",
            url: "https://newsletter.pragmaticengineer.com",
            type: "RSS",
          },
          { name: "a16z", url: "https://a16z.substack.com", type: "RSS" },
          { name: "Y Combinator Blog", url: "https://www.ycombinator.com/blog", type: "RSS" },
        ],
      },
      {
        label: "Redes sociais",
        sources: [
          { name: "Twitter/X (4 territories)", url: "https://x.com", type: "API" },
          { name: "Reddit (5 subreddits)", url: "https://reddit.com", type: "API" },
          { name: "Bluesky (2 queries)", url: "https://bsky.app", type: "API" },
          { name: "LinkedIn (2 queries)", url: "https://linkedin.com", type: "API" },
          { name: "Google News (3 queries)", url: "https://news.google.com", type: "API" },
        ],
      },
    ],
  },
  {
    agent: "RADAR",
    color: "#59FFB4",
    description: "Detecção de tendências emergentes e sinais fracos",
    categories: [
      {
        label: "Comunidades dev",
        sources: [
          {
            name: "Hacker News (best + show + ask)",
            url: "https://news.ycombinator.com",
            type: "RSS",
          },
          { name: "Lobsters", url: "https://lobste.rs", type: "RSS" },
          { name: "Product Hunt", url: "https://www.producthunt.com", type: "API" },
          { name: "Reddit (7 subreddits)", url: "https://reddit.com", type: "API" },
          { name: "Bluesky", url: "https://bsky.app", type: "API" },
        ],
      },
      {
        label: "Pesquisa acadêmica",
        sources: [
          { name: "arXiv CS.AI", url: "https://arxiv.org/list/cs.AI", type: "RSS" },
          { name: "arXiv CS.LG", url: "https://arxiv.org/list/cs.LG", type: "RSS" },
          { name: "arXiv CS.CL", url: "https://arxiv.org/list/cs.CL", type: "RSS" },
        ],
      },
      {
        label: "Código e repositórios",
        sources: [
          { name: "GitHub Trending (daily)", url: "https://github.com/trending", type: "API" },
          { name: "GitHub Trending (weekly)", url: "https://github.com/trending", type: "API" },
        ],
      },
      {
        label: "Tendências de busca",
        sources: [
          { name: "Google Trends Brasil", url: "https://trends.google.com", type: "API" },
          {
            name: "Google Trends (related queries)",
            url: "https://trends.google.com",
            type: "API",
          },
          { name: "Google News (2 queries)", url: "https://news.google.com", type: "API" },
        ],
      },
      {
        label: "Crypto e DeFi",
        sources: [
          { name: "CoinDesk", url: "https://www.coindesk.com", type: "RSS" },
          { name: "Cointelegraph DeFi", url: "https://cointelegraph.com", type: "RSS" },
          { name: "Decrypt", url: "https://decrypt.co", type: "RSS" },
          { name: "The Block", url: "https://www.theblock.co", type: "RSS" },
          { name: "Fintech News", url: "https://fintechnews.am", type: "RSS" },
        ],
      },
    ],
  },
  {
    agent: "CODIGO",
    color: "#59B4FF",
    description: "Ecossistema dev: frameworks, ferramentas e infraestrutura",
    categories: [
      {
        label: "Registros de pacotes",
        sources: [
          { name: "PyPI (novos + atualizados)", url: "https://pypi.org", type: "RSS" },
          { name: "npm Registry", url: "https://www.npmjs.com", type: "API" },
        ],
      },
      {
        label: "Código e repositórios",
        sources: [
          { name: "GitHub Trending (daily)", url: "https://github.com/trending", type: "API" },
          { name: "GitHub Trending (weekly)", url: "https://github.com/trending", type: "API" },
          { name: "GitHub Trending Fintech", url: "https://github.com/trending", type: "API" },
          { name: "Stack Overflow (tags trending)", url: "https://stackoverflow.com", type: "API" },
        ],
      },
      {
        label: "Publicações dev",
        sources: [
          { name: "InfoQ", url: "https://www.infoq.com", type: "RSS" },
          { name: "Dev.to", url: "https://dev.to", type: "RSS" },
          { name: "Changelog", url: "https://changelog.com", type: "RSS" },
          { name: "Cloudflare Blog", url: "https://blog.cloudflare.com", type: "RSS" },
          { name: "GitHub Blog", url: "https://github.blog", type: "RSS" },
          { name: "Vercel Blog", url: "https://vercel.com", type: "RSS" },
          { name: "Ethereum Blog", url: "https://blog.ethereum.org", type: "RSS" },
        ],
      },
      {
        label: "Comunidades",
        sources: [
          { name: "Reddit (6 subreddits dev)", url: "https://reddit.com", type: "API" },
          { name: "Product Hunt API", url: "https://www.producthunt.com", type: "API" },
        ],
      },
    ],
  },
  {
    agent: "FUNDING",
    color: "#FF8A59",
    description: "Rastreamento de rodadas de investimento em toda LATAM",
    categories: [
      {
        label: "Blogs de VCs",
        sources: [
          { name: "Kaszek", url: "https://kaszek.com", type: "RSS" },
          { name: "a16z", url: "https://a16z.substack.com", type: "RSS" },
          { name: "Sequoia Capital", url: "https://www.sequoiacap.com", type: "RSS" },
          { name: "Lightspeed Venture Partners", url: "https://lsvp.com", type: "RSS" },
          { name: "Greylock", url: "https://greylock.com", type: "RSS" },
          { name: "Y Combinator", url: "https://www.ycombinator.com/blog", type: "RSS" },
          { name: "LAVCA", url: "https://www.lavca.org", type: "RSS" },
        ],
      },
      {
        label: "News de funding",
        sources: [
          { name: "Crunchbase News", url: "https://news.crunchbase.com", type: "RSS" },
          {
            name: "TechCrunch Latin America",
            url: "https://techcrunch.com/tag/latin-america",
            type: "RSS",
          },
          { name: "LatamList", url: "https://latamlist.com", type: "RSS" },
          { name: "ABStartups", url: "https://abstartups.com.br", type: "RSS" },
          { name: "NeoFeed", url: "https://neofeed.com.br", type: "RSS" },
          { name: "Bloomberg Linea", url: "https://www.bloomberglinea.com.br", type: "RSS" },
        ],
      },
      {
        label: "Bases de dados",
        sources: [
          { name: "Crunchbase API", url: "https://www.crunchbase.com", type: "API" },
          { name: "Dealroom API", url: "https://dealroom.co", type: "API" },
          { name: "Google News (2 queries)", url: "https://news.google.com", type: "API" },
        ],
      },
      {
        label: "Registros regulatórios",
        sources: [
          {
            name: "SEC EDGAR Form D",
            url: "https://www.sec.gov/cgi-bin/browse-edgar",
            type: "API",
          },
        ],
      },
    ],
  },
  {
    agent: "MERCADO",
    color: "#C459FF",
    description: "Mapeamento do ecossistema tech em 17 paises LATAM",
    categories: [
      {
        label: "GitHub Search (21 cidades)",
        sources: [
          {
            name: "São Paulo, Rio, BH, Curitiba, POA, Floripa, Campinas, Recife",
            url: "https://api.github.com",
            type: "API",
          },
          { name: "CDMX, Guadalajara, Monterrey", url: "https://api.github.com", type: "API" },
          { name: "Buenos Aires, Córdoba", url: "https://api.github.com", type: "API" },
          {
            name: "Bogotá, Medellin, Santiago, Lima, Montevidéu, Quito, San José, Panamá",
            url: "https://api.github.com",
            type: "API",
          },
        ],
      },
      {
        label: "Bases de dados",
        sources: [
          { name: "Crunchbase API", url: "https://www.crunchbase.com", type: "API" },
          { name: "Dealroom API", url: "https://dealroom.co", type: "API" },
          { name: "LinkedIn (RapidAPI)", url: "https://linkedin.com", type: "API" },
          { name: "Google Trends LATAM", url: "https://trends.google.com", type: "API" },
        ],
      },
      {
        label: "Registros regulatórios",
        sources: [
          { name: "BCB (Banco Central do Brasil)", url: "https://www.bcb.gov.br", type: "API" },
        ],
      },
      {
        label: "Enriquecimento",
        sources: [{ name: "Gupy Jobs (tech stack)", url: "https://www.gupy.io", type: "API" }],
      },
    ],
  },
  {
    agent: "INDEX",
    color: "#E8FF59",
    description: "Registro abrangente de startups LATAM com dados regulatórios",
    categories: [
      {
        label: "Registros oficiais",
        sources: [
          { name: "Receita Federal (CNPJ)", url: "https://dados.gov.br", type: "Bulk CSV" },
          { name: "BCB (instituições autorizadas)", url: "https://www.bcb.gov.br", type: "API" },
        ],
      },
      {
        label: "Diretórios de startups",
        sources: [
          { name: "ABStartups StartupBase", url: "https://startupbase.com.br", type: "API" },
          {
            name: "Y Combinator Portfolio",
            url: "https://www.ycombinator.com/companies",
            type: "API",
          },
          { name: "StartupsLatam", url: "https://startupslatam.com", type: "API" },
        ],
      },
      {
        label: "Bases de dados comerciais",
        sources: [
          { name: "Crunchbase API", url: "https://www.crunchbase.com", type: "API" },
          { name: "Crunchbase Open Data", url: "https://www.crunchbase.com", type: "Bulk CSV" },
          { name: "CoreSignal", url: "https://coresignal.com", type: "API" },
        ],
      },
      {
        label: "GitHub Search (34 cidades)",
        sources: [{ name: "Cobertura completa LATAM", url: "https://api.github.com", type: "API" }],
      },
    ],
  },
];

function countSources(agents: AgentSources[]): number {
  return agents.reduce(
    (total, agent) =>
      total + agent.categories.reduce((catTotal, cat) => catTotal + cat.sources.length, 0),
    0,
  );
}

export default function FontesPage() {
  const totalSources = countSources(AGENT_SOURCES);

  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-[720px] px-6 py-16 md:px-10">
          <h1 className="font-display text-[clamp(28px,4vw,40px)] leading-[1.15] text-sinal-white">
            Fontes de Dados
          </h1>
          <p className="mt-4 text-[16px] leading-relaxed text-silver">
            Os agentes do Sinal monitoram {totalSources}+ fontes semanalmente: RSS feeds, APIs,
            registros de pacotes, repositórios, redes sociais, papers acadêmicos e bases
            regulatórias. Cada dado passa por um pipeline editorial de 6 camadas antes de ser
            publicado.
          </p>

          {/* Stats bar */}
          <div className="mt-8 flex flex-wrap gap-4">
            {[
              { label: "Fontes", value: `${totalSources}+` },
              { label: "Agentes", value: "6" },
              { label: "Países", value: "17" },
              { label: "Cidades", value: "21+" },
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-lg border border-[rgba(255,255,255,0.04)] bg-sinal-graphite px-4 py-2.5"
              >
                <span className="font-mono text-[18px] font-bold text-signal">{stat.value}</span>
                <span className="ml-2 font-mono text-[11px] uppercase tracking-wider text-ash">
                  {stat.label}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-12 space-y-12">
            {AGENT_SOURCES.map((agent) => (
              <section key={agent.agent}>
                <div className="mb-2 flex items-center gap-2">
                  <span
                    className="inline-block h-[6px] w-[6px] rounded-full"
                    style={{ backgroundColor: agent.color }}
                    aria-hidden="true"
                  />
                  <h2
                    className="font-mono text-[13px] font-semibold uppercase tracking-[1.5px]"
                    style={{ color: agent.color }}
                  >
                    {agent.agent}
                  </h2>
                </div>
                <p className="mb-5 text-[14px] text-ash">{agent.description}</p>

                <div className="space-y-4">
                  {agent.categories.map((cat) => (
                    <div key={cat.label}>
                      <h3 className="mb-2 font-mono text-[11px] uppercase tracking-wider text-bone/60">
                        {cat.label}
                      </h3>
                      <ul className="space-y-1.5">
                        {cat.sources.map((src) => (
                          <li
                            key={src.name}
                            className="flex items-center justify-between rounded-lg border border-[rgba(255,255,255,0.03)] bg-sinal-graphite/60 px-4 py-2.5"
                          >
                            <a
                              href={src.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[13px] text-silver transition-colors hover:text-sinal-white"
                            >
                              {src.name}
                            </a>
                            <span className="shrink-0 rounded-md bg-[rgba(255,255,255,0.04)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-ash">
                              {src.type}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <div className="mt-16 rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-6">
            <p className="font-mono text-[12px] text-ash">
              <strong className="text-bone">Pipeline editorial:</strong> Dados coletados por agentes
              autônomos, verificados por 6 camadas (pesquisa, validação, verificação, viés, SEO,
              síntese final). Cada item publicado inclui score de confiança e proveniência
              rastreável. Fontes marcadas como API requerem chaves de acesso. Algumas fontes estão
              em fase de integração.
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

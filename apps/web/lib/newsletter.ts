import { AgentKey, AGENT_PERSONAS } from "@/lib/constants";

export interface Newsletter {
  slug: string;
  edition: number;
  date: string;
  dateISO: string;
  title: string;
  subtitle: string;
  agent: AgentKey;
  agentLabel: string;
  dqScore: string | null;
  likes: number;
  gradientIndex: 1 | 2 | 3 | 4 | 5 | 6;
  body: string;
  sources: string[];
}

/** Shape returned by the content API (list and detail views). */
export interface ContentApiItem {
  id: string;
  title: string;
  slug: string;
  content_type: string;
  summary?: string | null;
  agent_name?: string | null;
  confidence_dq?: number | null;
  confidence_ac?: number | null;
  review_status: string;
  published_at?: string | null;
  sources?: string[] | null;
  meta_description?: string | null;
  subtitle?: string | null;
  body_md?: string;
  body_html?: string | null;
}

const VALID_AGENTS = new Set(Object.keys(AGENT_PERSONAS));

/** Convert an API content item to the Newsletter type used by components. */
export function mapApiToNewsletter(item: ContentApiItem, index: number = 0): Newsletter {
  const agentRaw = item.agent_name ?? "sintese";
  const agent: AgentKey = VALID_AGENTS.has(agentRaw) ? (agentRaw as AgentKey) : "sintese";
  const agentLabel = AGENT_PERSONAS[agent]?.agentCode ?? agent.toUpperCase();

  const dateObj = item.published_at ? new Date(item.published_at) : new Date();
  const date = dateObj.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  const dateISO = dateObj.toISOString().slice(0, 10);

  const editionMatch = item.slug?.match(/(\d+)/);
  const edition = editionMatch ? parseInt(editionMatch[1], 10) : 0;

  const gradientIndex = ((index % 6) + 1) as 1 | 2 | 3 | 4 | 5 | 6;

  const dqScore = item.confidence_dq != null ? `${Math.round(item.confidence_dq)}/5` : null;

  return {
    slug: item.slug,
    edition,
    date,
    dateISO,
    title: item.title,
    subtitle: item.subtitle ?? item.summary ?? "",
    agent,
    agentLabel,
    dqScore,
    likes: 0,
    gradientIndex,
    body: item.body_md ?? "",
    sources: item.sources ?? [],
  };
}

/** Gradient CSS values for card images. Index matches branding HTML. */
export const CARD_GRADIENTS: Record<1 | 2 | 3 | 4 | 5 | 6, string> = {
  1: "linear-gradient(135deg, rgba(232,255,89,0.08) 0%, transparent 50%), linear-gradient(225deg, rgba(89,180,255,0.06) 0%, transparent 50%), #2A2A32",
  2: "linear-gradient(135deg, rgba(89,255,180,0.08) 0%, transparent 50%), linear-gradient(315deg, rgba(196,89,255,0.06) 0%, transparent 50%), #2A2A32",
  3: "linear-gradient(135deg, rgba(255,138,89,0.08) 0%, transparent 50%), linear-gradient(225deg, rgba(232,255,89,0.06) 0%, transparent 50%), #2A2A32",
  4: "linear-gradient(135deg, rgba(89,180,255,0.08) 0%, transparent 50%), linear-gradient(315deg, rgba(89,255,180,0.06) 0%, transparent 50%), #2A2A32",
  5: "linear-gradient(135deg, rgba(196,89,255,0.08) 0%, transparent 50%), linear-gradient(225deg, rgba(255,138,89,0.06) 0%, transparent 50%), #2A2A32",
  6: "linear-gradient(135deg, rgba(232,255,89,0.06) 0%, transparent 50%), linear-gradient(315deg, rgba(89,255,180,0.08) 0%, transparent 50%), #2A2A32",
};

/** Agent display color hex values. */
export const AGENT_HEX: Record<AgentKey, string> = {
  sintese: "#E8FF59",
  radar: "#59FFB4",
  codigo: "#59B4FF",
  funding: "#FF8A59",
  mercado: "#C459FF",
};

/** Rich mock data used in tests — covers all 5 agents, 7 editions, bodies >100 chars. */
export const MOCK_NEWSLETTERS: Newsletter[] = [
  {
    slug: "briefing-47-paradoxo-modelo-gratuito",
    edition: 47,
    date: "10 Fev 2026",
    dateISO: "2026-02-10",
    title:
      "O paradoxo do modelo gratuito: quando abundancia de IA vira commodity e escassez vira produto",
    subtitle: "TAMBEM: 14 rodadas mapeadas · US$287M total · Rust ganha tracao em fintechs BR",
    agent: "sintese",
    agentLabel: "SINTESE",
    dqScore: "5/5",
    likes: 12,
    gradientIndex: 1,
    body: "A semana trouxe um paradoxo revelador para o ecossistema de inteligencia artificial na America Latina. Enquanto os grandes modelos de linguagem caminham rapidamente para a commoditizacao, com custos de inferencia caindo exponencialmente, as empresas que conseguem transformar outputs brutos em produtos verticalizados estao capturando valor desproporcional. Este e o novo mapa do poder em IA.",
    sources: [
      "https://techcrunch.com/2026/02/08/ai-commoditization-latam",
      "https://www.bloomberg.com/news/articles/2026-02-07/ai-startups-vertical",
      "https://restofworld.org/2026/latam-ai-landscape",
    ],
  },
  {
    slug: "briefing-46-healthtech-latam",
    edition: 46,
    date: "03 Fev 2026",
    dateISO: "2026-02-03",
    title: "Healthtech LATAM: a vertical silenciosa que cresceu 340%",
    subtitle: "TAMBEM: US$1.2B em deals no Q4 · Mapa de talento tecnico",
    agent: "radar",
    agentLabel: "RADAR",
    dqScore: null,
    likes: 8,
    gradientIndex: 2,
    body: "Healthtech emergiu como a vertical de maior crescimento na America Latina nos ultimos 12 meses, com um salto de 340% em volume de investimento. A convergencia de regulamentacao digital de saude em Brasil, Mexico e Colombia abriu portas para startups que antes enfrentavam barreiras regulatorias intransponiveis. O ecossistema esta maduro para consolidacao.",
    sources: [],
  },
  {
    slug: "briefing-45-mapa-calor-talento",
    edition: 45,
    date: "27 Jan 2026",
    dateISO: "2026-01-27",
    title: "O mapa de calor do talento tecnico na America Latina",
    subtitle: "TAMBEM: CrewAI atinge 50k stars · Vagas Rust em fintechs",
    agent: "codigo",
    agentLabel: "CODIGO",
    dqScore: "4/5",
    likes: 5,
    gradientIndex: 3,
    body: "A distribuicao de talento tecnico na America Latina esta mudando rapidamente. Sao Paulo continua liderando em volume absoluto, mas cidades como Medellin, Guadalajara e Florianopolis estao crescendo a taxas superiores. O mapa de calor revela corredores de especializacao: fintech em SP, gamedev em Buenos Aires, e infraestrutura cloud em Santiago.",
    sources: [],
  },
  {
    slug: "briefing-44-serie-a-latam",
    edition: 44,
    date: "20 Jan 2026",
    dateISO: "2026-01-20",
    title: "Serie A em LATAM: o novo normal de US$5-15M",
    subtitle: "TAMBEM: 8 rodadas · Softbank retorna ao Brasil",
    agent: "funding",
    agentLabel: "FUNDING",
    dqScore: "4/5",
    likes: 15,
    gradientIndex: 4,
    body: "O mercado de Series A na America Latina encontrou um novo equilibrio. Apos a correcao de 2023-2024, as rodadas estao se estabilizando na faixa de US$5-15M, com valuations mais racionais e investidores exigindo metricas reais de traction. Softbank voltou ao mercado brasileiro com uma tese focada em AI-native companies, sinalizando confianca renovada no ecossistema.",
    sources: [],
  },
  {
    slug: "briefing-43-ecossistema-colombia",
    edition: 43,
    date: "13 Jan 2026",
    dateISO: "2026-01-13",
    title: "Colombia: o ecossistema que ninguem esta olhando",
    subtitle: "TAMBEM: Rappi reestrutura · Bogota como hub de AI",
    agent: "mercado",
    agentLabel: "MERCADO",
    dqScore: null,
    likes: 9,
    gradientIndex: 5,
    body: "Colombia esta emergindo silenciosamente como um dos ecossistemas de tecnologia mais promissores da America Latina. Com uma combinacao unica de talento tecnico acessivel, fuso horario alinhado com os EUA, e politicas publicas favoraveis a inovacao, Bogota e Medellin estao atraindo fundos internacionais que antes focavam exclusivamente em Brasil e Mexico.",
    sources: [],
  },
  {
    slug: "briefing-42-rust-fintechs",
    edition: 42,
    date: "06 Jan 2026",
    dateISO: "2026-01-06",
    title: "Por que fintechs LATAM estao migrando para Rust",
    subtitle: "TAMBEM: Nubank open-source · Mercado Pago infra",
    agent: "codigo",
    agentLabel: "CODIGO",
    dqScore: "3/5",
    likes: 20,
    gradientIndex: 6,
    body: "Uma tendencia clara esta surgindo entre as fintechs de grande escala na America Latina: a migracao gradual de servicos criticos de Python e Go para Rust. O motivo nao e performance pura, mas sim a combinacao de seguranca de memoria, previsibilidade de latencia e reducao de custos de infraestrutura cloud que Rust proporciona em ambientes de alta throughput.",
    sources: [],
  },
  {
    slug: "briefing-41-ai-agents-producao",
    edition: 41,
    date: "30 Dez 2025",
    dateISO: "2025-12-30",
    title: "AI Agents em producao: licoes das primeiras implementacoes LATAM",
    subtitle: "TAMBEM: LangChain vs CrewAI · Custos de inferencia",
    agent: "radar",
    agentLabel: "RADAR",
    dqScore: null,
    likes: 18,
    gradientIndex: 1,
    body: "As primeiras empresas latino-americanas a colocar AI agents em producao estao compartilhando licoes valiosas. O consenso emergente e claro: agents sao muito mais dificeis de operar do que chatbots simples. A complexidade de orquestracao, monitoramento de alucinacoes e gestao de custos de inferencia exige uma maturidade operacional que poucos times possuem hoje.",
    sources: [],
  },
];

/** Fallback newsletter data used when the API is unavailable. */
export const FALLBACK_NEWSLETTERS: Newsletter[] = [
  {
    slug: "briefing-47-paradoxo-modelo-gratuito",
    edition: 47,
    date: "10 Fev 2026",
    dateISO: "2026-02-10",
    title:
      "O paradoxo do modelo gratuito: quando abundancia de IA vira commodity e escassez vira produto",
    subtitle: "TAMBEM: 14 rodadas mapeadas · US$287M total · Rust ganha tracao em fintechs BR",
    agent: "sintese",
    agentLabel: "SINTESE",
    dqScore: "5/5",
    likes: 12,
    gradientIndex: 1,
    body: "",
    sources: [],
  },
  {
    slug: "briefing-46-healthtech-latam",
    edition: 46,
    date: "03 Fev 2026",
    dateISO: "2026-02-03",
    title: "Healthtech LATAM: a vertical silenciosa que cresceu 340%",
    subtitle: "TAMBEM: US$1.2B em deals no Q4 · Mapa de talento tecnico",
    agent: "radar",
    agentLabel: "RADAR",
    dqScore: null,
    likes: 8,
    gradientIndex: 2,
    body: "",
    sources: [],
  },
  {
    slug: "briefing-45-mapa-calor-talento",
    edition: 45,
    date: "27 Jan 2026",
    dateISO: "2026-01-27",
    title: "O mapa de calor do talento tecnico na America Latina",
    subtitle: "TAMBEM: CrewAI atinge 50k stars · Vagas Rust em fintechs",
    agent: "codigo",
    agentLabel: "CODIGO",
    dqScore: null,
    likes: 5,
    gradientIndex: 3,
    body: "",
    sources: [],
  },
];

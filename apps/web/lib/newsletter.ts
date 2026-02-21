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
  },
];

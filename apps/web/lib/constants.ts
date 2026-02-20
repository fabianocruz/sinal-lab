/** Agent persona data for public-facing display. */
export const AGENT_PERSONAS = {
  sintese: {
    name: "Clara Medeiros",
    role: "Editora-chefe",
    agentCode: "SINTESE",
    color: "#E8FF59",
    description: "Curadoria editorial e síntese semanal",
    avatarPath: "/agents/clara-medeiros.jpg",
  },
  radar: {
    name: "Tomás Aguirre",
    role: "Analista de Tendências",
    agentCode: "RADAR",
    color: "#59FFB4",
    description: "Detecção de tendências emergentes",
    avatarPath: "/agents/tomas-aguirre.jpg",
  },
  codigo: {
    name: "Marina Costa",
    role: "Pesquisadora de Tecnologia",
    agentCode: "CODIGO",
    color: "#59B4FF",
    description: "Análise de código e infraestrutura",
    avatarPath: "/agents/marina-costa.jpg",
  },
  funding: {
    name: "Rafael Oliveira",
    role: "Analista de Investimentos",
    agentCode: "FUNDING",
    color: "#FF8A59",
    description: "Rastreamento de capital e rodadas",
    avatarPath: "/agents/rafael-oliveira.jpg",
  },
  mercado: {
    name: "Valentina Rojas",
    role: "Especialista LATAM",
    agentCode: "MERCADO",
    color: "#C459FF",
    description: "Inteligência de mercado regional",
    avatarPath: "/agents/valentina-rojas.jpg",
  },
} as const;

export type AgentKey = keyof typeof AGENT_PERSONAS;

/** Agent colors for Tailwind class usage. */
export const AGENT_COLORS: Record<AgentKey, string> = {
  sintese: "agent-sintese",
  radar: "agent-radar",
  codigo: "agent-codigo",
  funding: "agent-funding",
  mercado: "agent-mercado",
};

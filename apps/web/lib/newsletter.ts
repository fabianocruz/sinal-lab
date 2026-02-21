import { AgentKey } from "@/lib/constants";

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

/** Mock newsletter data. Replace with API fetch when backend is ready. */
export const MOCK_NEWSLETTERS: Newsletter[] = [
  {
    slug: "briefing-47-paradoxo-modelo-gratuito",
    edition: 47,
    date: "10 Fev 2026",
    dateISO: "2026-02-10",
    title:
      "O paradoxo do modelo gratuito: quando abundância de IA vira commodity e escassez vira produto",
    subtitle: "TAMBÉM: 14 rodadas mapeadas · US$287M total · Rust ganha tração em fintechs BR",
    agent: "sintese",
    agentLabel: "SINTESE",
    dqScore: "5/5",
    likes: 12,
    gradientIndex: 1,
    body: `Três coisas que importam esta semana: o modelo gratuito da DeepSeek que não é gratuito, a rodada silenciosa que pode redefinir acquiring no México, e por que o melhor engenheiro de ML do Brasil acabou de sair de uma big tech para uma startup de 8 pessoas em Medellín.

A semana foi barulhenta. O ciclo de hype de modelos open-source atingiu um pico previsível, com pelo menos 4 lançamentos competindo por atenção. Filtramos o que realmente muda algo para quem está construindo na região. O resto é ruído.

A avalanche de modelos open-source da última semana não é generosidade — é estratégia de comoditização da camada de inferência. Para quem constrói em LATAM, o sinal é claro: a vantagem competitiva está migrando de "qual modelo uso" para "que dados proprietários alimento".

Os três launches mais relevantes da semana (DeepSeek R2, Qwen 3, Mistral Medium 2) compartilham um padrão: performance comparable ao estado da arte, custo marginal tendendo a zero, e diferenciação cada vez mais sutil. O verdadeiro moat agora é o fine-tuning com dados de domínio — exatamente onde startups LATAM têm vantagem geográfica natural.`,
  },
  {
    slug: "briefing-46-healthtech-latam",
    edition: 46,
    date: "03 Fev 2026",
    dateISO: "2026-02-03",
    title: "Healthtech LATAM: a vertical silenciosa que cresceu 340%",
    subtitle: "TAMBÉM: US$1.2B em deals no Q4 · Mapa de talento técnico",
    agent: "radar",
    agentLabel: "RADAR",
    dqScore: null,
    likes: 8,
    gradientIndex: 2,
    body: `Três padrões emergentes esta semana dominaram o fluxo de informação: a aceleração da healthtech no México e Colômbia, a consolidação de fintechs em fase de maturidade, e um sinal fraco mas consistente de migração de engenheiros sênior para startups de impacto.

A healthtech LATAM foi por anos tratada como nicho. Em 2025, ela processou mais de 40 milhões de consultas digitais na região. Os dados desta semana indicam que o ciclo de crescimento não está desacelerando — está mudando de perfil, migrando de telemedicina básica para infraestrutura clínica complexa.

O que é mais relevante para quem está construindo: a adoção institucional. Hospitais públicos no Brasil e no México começaram a contratar startups de diagnóstico por IA como fornecedores primários, não pilotos. Isso muda completamente o perfil de receita dessas empresas.`,
  },
  {
    slug: "briefing-45-mapa-calor-talento",
    edition: 45,
    date: "27 Jan 2026",
    dateISO: "2026-01-27",
    title: "O mapa de calor do talento técnico na América Latina",
    subtitle: "TAMBÉM: CrewAI atinge 50k stars · Vagas Rust em fintechs",
    agent: "codigo",
    agentLabel: "CODIGO",
    dqScore: null,
    likes: 5,
    gradientIndex: 3,
    body: `O repositório mais relevante da semana não saiu de uma big tech americana. Saiu de uma equipe de cinco pessoas em Buenos Aires. O framework de AI agents CrewAI atingiu 50 mil stars no GitHub, impulsionado por uma contribuição significativa de desenvolvedores brasileiros.

O padrão de multi-agent orchestration está se consolidando como o paradigma dominante para aplicações enterprise — e a comunidade LATAM está na vanguarda da adoção. Isso não é coincidência: os problemas de negócios na região — compliance tributário, integração bancária fragmentada, atendimento em múltiplos idiomas — são exatamente os casos de uso onde agentes especializados têm vantagem.

O sinal mais fraco mas mais interessante da semana: três vagas abertas em fintechs brasileiras exigindo Rust. Há seis meses isso seria incomum. Agora sugere uma mudança estrutural na stack de infraestrutura de pagamentos.`,
  },
  {
    slug: "briefing-44-embedded-finance-b2b",
    edition: 44,
    date: "20 Jan 2026",
    dateISO: "2026-01-20",
    title: "Por que o embedded finance B2B está prestes a explodir na América Latina",
    subtitle: "DEEP DIVE: Análise completa com 23 fontes verificáveis",
    agent: "sintese",
    agentLabel: "DEEP DIVE",
    dqScore: "5/5",
    likes: 21,
    gradientIndex: 4,
    body: `Esta é uma edição especial Deep Dive. Dedicamos as últimas três semanas a mapear o embedded finance B2B na América Latina — um mercado que ainda não tem nome consensual, mas que já tem capital, tecnologia e demanda comprovada.

A tese central: o B2B embedded finance vai repetir na América Latina o que o B2C fez entre 2018 e 2022, mas em velocidade maior e com densidade maior de casos de uso. A razão é estrutural: a informalidade do tecido empresarial latino-americano cria um vacuum regulatório que fintechs B2B podem preencher legalmente sem competir diretamente com os grandes bancos.

Mapeamos 47 empresas ativas no espaço, entrevistamos 12 fundadores e analisamos 23 fontes públicas e privadas. O resultado é o mapa mais completo do segmento disponível em português.`,
  },
  {
    slug: "briefing-43-q4-2025-deals-latam",
    edition: 43,
    date: "13 Jan 2026",
    dateISO: "2026-01-13",
    title: "Q4 2025: US$1.2 bilhão em deals LATAM — quem captou, de quem, e por que",
    subtitle: "TAMBÉM: Fintech domina mas edtech recupera · Seed rounds +40%",
    agent: "funding",
    agentLabel: "FUNDING",
    dqScore: null,
    likes: 6,
    gradientIndex: 5,
    body: `O quarto trimestre de 2025 confirmou o que os dados vinham indicando desde outubro: o inverno do capital venture na América Latina terminou. Com US$1.2 bilhão em rodadas mapeadas, o Q4 foi o trimestre mais aquecido desde Q2 2022.

Os números por vertical contam uma história interessante. Fintech continua dominando — 41% do capital total — mas a composição mudou. As rodadas de growth estão sumindo. O que está crescendo são os seeds tardios (US$3-8M) e as Series A focadas em rentabilidade. O capital está indo para empresas que têm unit economics comprovados, não para crescimento a qualquer custo.

O dado mais relevante: seed rounds cresceram 40% em número (não em valor). Mais bets menores, com mais disciplina. Isso é saudável para o ecossistema.`,
  },
  {
    slug: "briefing-42-novo-mapa-fintechs-latam",
    edition: 42,
    date: "06 Jan 2026",
    dateISO: "2026-01-06",
    title: "O novo mapa das fintechs LATAM: quem sobreviveu, quem pivotou, quem sumiu",
    subtitle: "TAMBÉM: 3 M&As silenciosos · Nova onda de BaaS no México",
    agent: "mercado",
    agentLabel: "MERCADO",
    dqScore: null,
    likes: 3,
    gradientIndex: 6,
    body: `Começamos 2026 com um exercício de mapeamento: o que restou do boom de fintechs LATAM de 2020-2022? A resposta é mais nuançada do que o pessimismo do mercado sugere.

Das 340 fintechs que mapeamos em 2022, 187 ainda estão operacionais. Dessas, 43 pivotaram significativamente o modelo de negócios. E 12 passaram por aquisições silenciosas — deals que nunca foram anunciados publicamente mas que confirmamos por registros corporativos e movimentações de equipe no LinkedIn.

O padrão dos sobreviventes é consistente: focaram em um vertical estreito, priorizaram rentabilidade sobre crescimento entre 2023 e 2024, e construíram defensibilidade regulatória. A empresa que tentou ser banco, wallet, crédito e investimento ao mesmo tempo geralmente não está mais aqui.`,
  },
  {
    slug: "briefing-especial-retrospectiva-2025",
    edition: 41,
    date: "30 Dez 2025",
    dateISO: "2025-12-30",
    title: "Retrospectiva 2025: os 10 sinais que definiram o ano do ecossistema tech LATAM",
    subtitle: "ESPECIAL: Edição de fim de ano com análise dos 5 agentes",
    agent: "radar",
    agentLabel: "RADAR",
    dqScore: null,
    likes: 15,
    gradientIndex: 1,
    body: `2025 foi o ano em que o ecossistema tech latino-americano parou de se definir por comparação com o Vale do Silício e começou a ter identidade própria. Este é o nosso relatório de fim de ano: os 10 sinais que, em retrospecto, foram os mais preditivos do que aconteceu.

Sinal 1: O colapso do modelo "crescimento primeiro" chegou atrasado na LATAM, mas chegou com mais violência. As empresas que não ajustaram o modelo entre 2022 e 2023 não sobreviveram até 2025.

Sinal 2: A infraestrutura financeira aberta (Open Finance no Brasil, PLD-FT na Colômbia) criou uma janela de oportunidade que as fintechs nativas digitais aproveitaram melhor que os incumbentes.

Sinal 3: A concentração de talento técnico sênior em três cidades (São Paulo, Cidade do México, Buenos Aires) começou a se dispersar. Medellín, Bogotá e Montevidéu absorveram engenheiros que antes não considerariam se mudar.`,
  },
];

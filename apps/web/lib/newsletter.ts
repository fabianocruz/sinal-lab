import { AgentKey } from '@/lib/constants';

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
  1: 'linear-gradient(135deg, rgba(232,255,89,0.08) 0%, transparent 50%), linear-gradient(225deg, rgba(89,180,255,0.06) 0%, transparent 50%), #2A2A32',
  2: 'linear-gradient(135deg, rgba(89,255,180,0.08) 0%, transparent 50%), linear-gradient(315deg, rgba(196,89,255,0.06) 0%, transparent 50%), #2A2A32',
  3: 'linear-gradient(135deg, rgba(255,138,89,0.08) 0%, transparent 50%), linear-gradient(225deg, rgba(232,255,89,0.06) 0%, transparent 50%), #2A2A32',
  4: 'linear-gradient(135deg, rgba(89,180,255,0.08) 0%, transparent 50%), linear-gradient(315deg, rgba(89,255,180,0.06) 0%, transparent 50%), #2A2A32',
  5: 'linear-gradient(135deg, rgba(196,89,255,0.08) 0%, transparent 50%), linear-gradient(225deg, rgba(255,138,89,0.06) 0%, transparent 50%), #2A2A32',
  6: 'linear-gradient(135deg, rgba(232,255,89,0.06) 0%, transparent 50%), linear-gradient(315deg, rgba(89,255,180,0.08) 0%, transparent 50%), #2A2A32',
};

/** Agent display color hex values. */
export const AGENT_HEX: Record<AgentKey, string> = {
  sintese: '#E8FF59',
  radar: '#59FFB4',
  codigo: '#59B4FF',
  funding: '#FF8A59',
  mercado: '#C459FF',
};

/** Mock newsletter data. Replace with API fetch when backend is ready. */
export const MOCK_NEWSLETTERS: Newsletter[] = [
  {
    slug: 'briefing-47-paradoxo-modelo-gratuito',
    edition: 47,
    date: '10 Fev 2026',
    dateISO: '2026-02-10',
    title: 'O paradoxo do modelo gratuito: quando abundancia de IA vira commodity e escassez vira produto',
    subtitle: 'TAMBEM: 14 rodadas mapeadas · US$287M total · Rust ganha tracao em fintechs BR',
    agent: 'sintese',
    agentLabel: 'SINTESE',
    dqScore: '5/5',
    likes: 12,
    gradientIndex: 1,
    body: `Tres coisas que importam esta semana: o modelo gratuito da DeepSeek que nao e gratuito, a rodada silenciosa que pode redefinir acquiring no Mexico, e por que o melhor engenheiro de ML do Brasil acabou de sair de uma big tech para uma startup de 8 pessoas em Medellin.

A semana foi barulhenta. O ciclo de hype de modelos open-source atingiu um pico previsivel, com pelo menos 4 lancamentos competindo por atencao. Filtramos o que realmente muda algo para quem esta construindo na regiao. O resto e ruido.

A avalanche de modelos open-source da ultima semana nao e generosidade — e estrategia de comoditizacao da camada de inferencia. Para quem constroi em LATAM, o sinal e claro: a vantagem competitiva esta migrando de "qual modelo uso" para "que dados proprietarios alimento".

Os tres launches mais relevantes da semana (DeepSeek R2, Qwen 3, Mistral Medium 2) compartilham um padrao: performance comparable ao estado da arte, custo marginal tendendo a zero, e diferenciacao cada vez mais sutil. O verdadeiro moat agora e o fine-tuning com dados de dominio — exatamente onde startups LATAM tem vantagem geografica natural.`,
  },
  {
    slug: 'briefing-46-healthtech-latam',
    edition: 46,
    date: '03 Fev 2026',
    dateISO: '2026-02-03',
    title: 'Healthtech LATAM: a vertical silenciosa que cresceu 340%',
    subtitle: 'TAMBEM: US$1.2B em deals no Q4 · Mapa de talento tecnico',
    agent: 'radar',
    agentLabel: 'RADAR',
    dqScore: null,
    likes: 8,
    gradientIndex: 2,
    body: `Tres padroes emergentes esta semana dominaram o fluxo de informacao: a aceleracao da healthtech no Mexico e Colombia, a consolidacao de fintechs em fase de maturidade, e um sinal fraco mas consistente de migracao de engenheiros senior para startups de impacto.

A healthtech LATAM foi por anos tratada como nicho. Em 2025, ela processou mais de 40 milhoes de consultas digitais na regiao. Os dados desta semana indicam que o ciclo de crescimento nao esta desacelerando — esta mudando de perfil, migrando de telemedicina basica para infraestrutura clinica complexa.

O que e mais relevante para quem esta construindo: a adocao institucional. Hospitais publicos no Brasil e no Mexico comecaram a contratar startups de diagnostico por IA como fornecedores primarios, nao pilotos. Isso muda completamente o perfil de receita dessas empresas.`,
  },
  {
    slug: 'briefing-45-mapa-calor-talento',
    edition: 45,
    date: '27 Jan 2026',
    dateISO: '2026-01-27',
    title: 'O mapa de calor do talento tecnico na America Latina',
    subtitle: 'TAMBEM: CrewAI atinge 50k stars · Vagas Rust em fintechs',
    agent: 'codigo',
    agentLabel: 'CODIGO',
    dqScore: null,
    likes: 5,
    gradientIndex: 3,
    body: `O repositorio mais relevante da semana nao saiu de uma big tech americana. Saiu de uma equipe de cinco pessoas em Buenos Aires. O framework de AI agents CrewAI atingiu 50 mil stars no GitHub, impulsionado por uma contribuicao significativa de desenvolvedores brasileiros.

O padrao de multi-agent orchestration esta se consolidando como o paradigma dominante para aplicacoes enterprise — e a comunidade LATAM esta na vanguarda da adocao. Isso nao e coincidencia: os problemas de negocio na regiao — compliance tributario, integracao bancaria fragmentada, atendimento em multiplos idiomas — sao exatamente os casos de uso onde agentes especializados tem vantagem.

O sinal mais fraco mas mais interessante da semana: tres vagas abertas em fintechs brasileiras exigindo Rust. Ha seis meses isso seria incomum. Agora sugere uma mudanca estrutural na stack de infraestrutura de pagamentos.`,
  },
  {
    slug: 'briefing-44-embedded-finance-b2b',
    edition: 44,
    date: '20 Jan 2026',
    dateISO: '2026-01-20',
    title: 'Por que o embedded finance B2B esta prestes a explodir na America Latina',
    subtitle: 'DEEP DIVE: Analise completa com 23 fontes verificaveis',
    agent: 'sintese',
    agentLabel: 'DEEP DIVE',
    dqScore: '5/5',
    likes: 21,
    gradientIndex: 4,
    body: `Esta e uma edicao especial Deep Dive. Dedicamos as ultimas tres semanas a mapear o embedded finance B2B na America Latina — um mercado que ainda nao tem nome consensual, mas que ja tem capital, tecnologia e demanda comprovada.

A tese central: o B2B embedded finance vai repetir na America Latina o que o B2C fez entre 2018 e 2022, mas em velocidade maior e com densidade maior de casos de uso. A razao e estrutural: a informalidade do tecido empresarial latino-americano cria um vacuum regulatorio que fintechs B2B podem preencher legalmente sem competir diretamente com os grandes bancos.

Mapeamos 47 empresas ativas no espaco, entrevistamos 12 fundadores e analisamos 23 fontes publicas e privadas. O resultado e o mapa mais completo do segmento disponivel em portugues.`,
  },
  {
    slug: 'briefing-43-q4-2025-deals-latam',
    edition: 43,
    date: '13 Jan 2026',
    dateISO: '2026-01-13',
    title: 'Q4 2025: US$1.2 bilhao em deals LATAM — quem captou, de quem, e por que',
    subtitle: 'TAMBEM: Fintech domina mas edtech recupera · Seed rounds +40%',
    agent: 'funding',
    agentLabel: 'FUNDING',
    dqScore: null,
    likes: 6,
    gradientIndex: 5,
    body: `O quarto trimestre de 2025 confirmou o que os dados vinham indicando desde outubro: o inverno do capital venture na America Latina terminou. Com US$1.2 bilhao em rodadas mapeadas, o Q4 foi o trimestre mais aquecido desde Q2 2022.

Os numeros por vertical contam uma historia interessante. Fintech continua dominando — 41% do capital total — mas a composicao mudou. As rodadas de growth estao sumindo. O que esta crescendo sao os seeds tardios (US$3-8M) e as Series A focadas em rentabilidade. O capital esta indo para empresas que tem unit economics comprovados, nao para crescimento a qualquer custo.

O dado mais relevante: seed rounds cresceram 40% em numero (nao em valor). Mais bets menores, com mais disciplina. Isso e saudavel para o ecossistema.`,
  },
  {
    slug: 'briefing-42-novo-mapa-fintechs-latam',
    edition: 42,
    date: '06 Jan 2026',
    dateISO: '2026-01-06',
    title: 'O novo mapa das fintechs LATAM: quem sobreviveu, quem pivotou, quem sumiu',
    subtitle: 'TAMBEM: 3 M&As silenciosos · Nova onda de BaaS no Mexico',
    agent: 'mercado',
    agentLabel: 'MERCADO',
    dqScore: null,
    likes: 3,
    gradientIndex: 6,
    body: `Comecamos 2026 com um exercicio de mapeamento: o que restou do boom de fintechs LATAM de 2020-2022? A resposta e mais nuancada do que o pessimismo do mercado sugere.

Das 340 fintechs que mapeamos em 2022, 187 ainda estao operacionais. Dessas, 43 pivotaram significativamente o modelo de negocio. E 12 passaram por aquisicoes silenciosas — deals que nunca foram anunciados publicamente mas que confirmamos por registros corporativos e movimentacoes de equipe no LinkedIn.

O padrao dos sobreviventes e consistente: focaram em um vertical estreito, priorizaram rentabilidade sobre crescimento entre 2023 e 2024, e construiram defensibilidade regulatoria. A empresa que tentou ser banco, wallet, credito e investimento ao mesmo tempo geralmente nao esta mais aqui.`,
  },
  {
    slug: 'briefing-especial-retrospectiva-2025',
    edition: 41,
    date: '30 Dez 2025',
    dateISO: '2025-12-30',
    title: 'Retrospectiva 2025: os 10 sinais que definiram o ano do ecossistema tech LATAM',
    subtitle: 'ESPECIAL: Edicao de fim de ano com analise dos 5 agentes',
    agent: 'radar',
    agentLabel: 'RADAR',
    dqScore: null,
    likes: 15,
    gradientIndex: 1,
    body: `2025 foi o ano em que o ecossistema tech latino-americano parou de se definir por comparacao com o Vale do Silicio e comecou a ter identidade propria. Este e o nosso relatorio de fim de ano: os 10 sinais que, em retrospecto, foram os mais preditivos do que aconteceu.

Sinal 1: O colapso do modelo "crescimento primeiro" chegou atrasado na LATAM, mas chegou com mais violencia. As empresas que nao ajustaram o modelo entre 2022 e 2023 nao sobreviveram ate 2025.

Sinal 2: A infraestrutura financeira aberta (Open Finance no Brasil, PLD-FT na Colombia) criou uma janela de oportunidade que as fintechs nativas digitais aproveitaram melhor que os incumbentes.

Sinal 3: A concentracao de talento tecnico senior em tres cidades (Sao Paulo, Cidade do Mexico, Buenos Aires) comecou a se dispersar. Medellín, Bogota e Montevideu absorveram engenheiros que antes nao considerariam se mudar.`,
  },
];

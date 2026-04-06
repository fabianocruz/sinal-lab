/**
 * Structured API documentation data — single source of truth for /developers.
 *
 * All endpoint params, response fields and code examples come from the real
 * FastAPI routers in apps/api/routers/ and schemas in apps/api/schemas/.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApiParam {
  name: string;
  type: string;
  required: boolean;
  default?: string;
  description: string;
}

export interface ApiField {
  name: string;
  type: string;
  description: string;
}

export interface CodeExample {
  curl: string;
  python: string;
  javascript: string;
}

export interface EndpointDoc {
  method: "GET" | "POST";
  path: string;
  description: string;
  params: ApiParam[];
  responseFields: ApiField[];
  examples: CodeExample;
  exampleResponse: string;
}

export interface ApiGroup {
  id: string;
  name: string;
  label: string;
  description: string;
  color: string;
  fieldCount: string;
  endpoints: EndpointDoc[];
  comingSoon?: boolean;
}

export interface SidebarSection {
  id: string;
  label: string;
}

// ---------------------------------------------------------------------------
// Base URL placeholder (replaced by real domain when keys are issued)
// ---------------------------------------------------------------------------

const BASE = "https://api.sinal.tech";

// ---------------------------------------------------------------------------
// Sidebar sections
// ---------------------------------------------------------------------------

export const SIDEBAR_SECTIONS: SidebarSection[] = [
  { id: "visao-geral", label: "Visão Geral" },
  { id: "autenticacao", label: "Autenticação" },
  { id: "empresas", label: "Empresas" },
  { id: "conteudo", label: "Conteúdo" },
  { id: "agentes", label: "Agentes" },
  { id: "sinais", label: "Sinais" },
  { id: "investimentos", label: "Investimentos" },
  { id: "paginacao", label: "Paginação" },
  { id: "erros", label: "Erros" },
  { id: "solicitar-acesso", label: "Solicitar Acesso" },
];

// ---------------------------------------------------------------------------
// Shared pagination params (DRY)
// ---------------------------------------------------------------------------

const PAGINATION_PARAMS: ApiParam[] = [
  {
    name: "limit",
    type: "int",
    required: false,
    default: "20",
    description: "Itens por página (max 100)",
  },
  {
    name: "offset",
    type: "int",
    required: false,
    default: "0",
    description: "Deslocamento para paginação",
  },
];

// ---------------------------------------------------------------------------
// Companies API
// ---------------------------------------------------------------------------

const COMPANIES_FIELDS: ApiField[] = [
  { name: "id", type: "UUID", description: "Identificador único" },
  { name: "name", type: "string", description: "Nome da empresa" },
  { name: "slug", type: "string", description: "Slug URL-friendly" },
  { name: "description", type: "string?", description: "Descrição completa" },
  { name: "short_description", type: "string?", description: "Descrição curta" },
  { name: "sector", type: "string?", description: "Setor (ex: Fintech, SaaS)" },
  { name: "sub_sector", type: "string?", description: "Sub-setor" },
  { name: "city", type: "string?", description: "Cidade sede" },
  { name: "state", type: "string?", description: "Estado" },
  { name: "country", type: "string", description: "País (default: Brazil)" },
  { name: "tags", type: "string[]?", description: "Tags descritivas" },
  { name: "tech_stack", type: "string[]?", description: "Tecnologias usadas" },
  { name: "founded_date", type: "date?", description: "Data de fundação" },
  { name: "team_size", type: "int?", description: "Tamanho da equipe" },
  { name: "business_model", type: "string?", description: "Modelo de negócio" },
  { name: "website", type: "string?", description: "URL do site" },
  { name: "github_url", type: "string?", description: "URL do GitHub" },
  { name: "linkedin_url", type: "string?", description: "URL do LinkedIn" },
  { name: "twitter_url", type: "string?", description: "URL do Twitter/X" },
  { name: "source_count", type: "int", description: "Número de fontes verificadas" },
  { name: "status", type: "string", description: "Status (active, inactive)" },
  { name: "created_at", type: "datetime?", description: "Data de criação no sistema" },
];

const companiesApi: ApiGroup = {
  id: "empresas",
  name: "Empresas",
  label: "API DE EMPRESAS",
  description:
    "Startups e empresas do ecossistema tech da América Latina com filtros por setor, cidade, país e tags.",
  color: "#59FFB4",
  fieldCount: "22 campos",
  endpoints: [
    {
      method: "GET",
      path: "/api/companies",
      description: "Lista empresas com filtros opcionais e paginação.",
      params: [
        {
          name: "sector",
          type: "string",
          required: false,
          description: "Filtra por setor (ex: Fintech, SaaS)",
        },
        {
          name: "city",
          type: "string",
          required: false,
          description: "Filtra por cidade (ex: São Paulo)",
        },
        {
          name: "country",
          type: "string",
          required: false,
          description: "Filtra por país (ex: Brazil, Mexico)",
        },
        {
          name: "status",
          type: "string",
          required: false,
          default: "active",
          description: "Status da empresa",
        },
        {
          name: "search",
          type: "string",
          required: false,
          description: "Busca no nome (case-insensitive)",
        },
        {
          name: "tags",
          type: "string",
          required: false,
          description: "Filtra por tag (JSON contains)",
        },
        ...PAGINATION_PARAMS,
      ],
      responseFields: COMPANIES_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/companies?sector=Fintech&limit=5"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/companies",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"sector": "Fintech", "limit": 5},
)
data = resp.json()
print(f"{data['total']} empresas encontradas")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/companies?sector=Fintech&limit=5",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const data = await resp.json();
console.log(\`\${data.total} empresas encontradas\`);`,
      },
      exampleResponse: `{
  "items": [
    {
      "name": "Nubank",
      "slug": "nubank",
      "sector": "Fintech",
      "country": "Brazil",
      "city": "Sao Paulo",
      "tags": ["neobank", "fintech", "payments"],
      "tech_stack": ["Clojure", "Kafka", "Datomic"],
      "team_size": 8000,
      "source_count": 12,
      "status": "active"
    }
  ],
  "total": 847,
  "limit": 5,
  "offset": 0
}`,
    },
    {
      method: "GET",
      path: "/api/companies/{slug}",
      description: "Retorna o perfil completo de uma empresa pelo slug.",
      params: [
        {
          name: "slug",
          type: "string",
          required: true,
          description: "Slug da empresa (ex: nubank)",
        },
      ],
      responseFields: [
        ...COMPANIES_FIELDS,
        { name: "metadata_", type: "object?", description: "Metadados adicionais" },
      ],
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/companies/nubank"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/companies/nubank",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
)
company = resp.json()
print(company["name"], "-", company["sector"])`,
        javascript: `const resp = await fetch(
  "${BASE}/api/companies/nubank",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const company = await resp.json();
console.log(company.name, "-", company.sector);`,
      },
      exampleResponse: `{
  "id": "a1b2c3d4-...",
  "name": "Nubank",
  "slug": "nubank",
  "sector": "Fintech",
  "sub_sector": "Neobank",
  "city": "Sao Paulo",
  "country": "Brazil",
  "tags": ["neobank", "fintech", "payments"],
  "tech_stack": ["Clojure", "Kafka", "Datomic"],
  "founded_date": "2013-05-06",
  "team_size": 8000,
  "website": "https://nubank.com.br",
  "source_count": 12,
  "status": "active"
}`,
    },
  ],
};

// ---------------------------------------------------------------------------
// Content API
// ---------------------------------------------------------------------------

const CONTENT_FIELDS: ApiField[] = [
  { name: "id", type: "UUID", description: "Identificador único" },
  { name: "title", type: "string", description: "Título do conteúdo" },
  { name: "slug", type: "string", description: "Slug URL-friendly" },
  { name: "subtitle", type: "string?", description: "Subtítulo" },
  {
    name: "content_type",
    type: "string",
    description: "Tipo: DATA_REPORT, ANALYSIS, DEEP_DIVE, ARTICLE, etc.",
  },
  { name: "summary", type: "string?", description: "Resumo do conteúdo" },
  {
    name: "agent_name",
    type: "string?",
    description: "Agente que gerou (sintese, radar, codigo, etc.)",
  },
  { name: "confidence_dq", type: "float?", description: "Score de qualidade de dados (0-1)" },
  { name: "confidence_ac", type: "float?", description: "Score de confiança analítica (0-1)" },
  {
    name: "review_status",
    type: "string",
    description: "Status: draft, review, published, retracted",
  },
  { name: "published_at", type: "datetime?", description: "Data de publicação" },
  { name: "sources", type: "string[]?", description: "URLs das fontes utilizadas" },
  { name: "meta_description", type: "string?", description: "Descrição para SEO" },
  { name: "author_name", type: "string?", description: "Nome do autor/agente" },
];

const contentApi: ApiGroup = {
  id: "conteudo",
  name: "Conteúdo",
  label: "API DE CONTEÚDO",
  description:
    "Conteúdo editorial gerado por AI agents — newsletters, trend reports, análises e deep dives.",
  color: "#E8FF59",
  fieldCount: "14 campos",
  endpoints: [
    {
      method: "GET",
      path: "/api/content",
      description: "Lista conteúdo publicado com filtros e paginação.",
      params: [
        {
          name: "content_type",
          type: "string",
          required: false,
          description: "Filtra tipo (DATA_REPORT, ANALYSIS, DEEP_DIVE, etc.)",
        },
        {
          name: "content_type_exclude",
          type: "string",
          required: false,
          description: "Exclui um tipo de conteúdo",
        },
        {
          name: "agent_name",
          type: "string",
          required: false,
          description: "Filtra por agente (sintese, radar, codigo)",
        },
        {
          name: "status",
          type: "string",
          required: false,
          description: "Status de revisão (published, draft)",
        },
        {
          name: "search",
          type: "string",
          required: false,
          description: "Busca no título (case-insensitive)",
        },
        ...PAGINATION_PARAMS,
      ],
      responseFields: CONTENT_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/content?content_type=DATA_REPORT&limit=5"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/content",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"content_type": "DATA_REPORT", "limit": 5},
)
data = resp.json()
for item in data["items"]:
    print(item["title"], f"(DQ: {item['confidence_dq']})")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/content?content_type=DATA_REPORT&limit=5",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const data = await resp.json();
data.items.forEach(item =>
  console.log(item.title, \`(DQ: \${item.confidence_dq})\`)
);`,
      },
      exampleResponse: `{
  "items": [
    {
      "title": "Sinal Semanal #48",
      "slug": "sinal-semanal-48",
      "content_type": "DATA_REPORT",
      "agent_name": "sintese",
      "confidence_dq": 0.87,
      "confidence_ac": 0.82,
      "review_status": "published",
      "published_at": "2026-02-23T10:00:00Z",
      "sources": ["techcrunch.com", "bloomberg.com"]
    }
  ],
  "total": 156,
  "limit": 5,
  "offset": 0
}`,
    },
    {
      method: "GET",
      path: "/api/content/{slug}",
      description: "Retorna o conteúdo completo pelo slug, incluindo corpo em Markdown.",
      params: [{ name: "slug", type: "string", required: true, description: "Slug do conteúdo" }],
      responseFields: [
        ...CONTENT_FIELDS,
        { name: "body_md", type: "string", description: "Corpo completo em Markdown" },
        { name: "body_html", type: "string?", description: "Corpo renderizado em HTML" },
        { name: "canonical_url", type: "string?", description: "URL canônica" },
      ],
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/content/sinal-semanal-48"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/content/sinal-semanal-48",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
)
article = resp.json()
print(article["title"])
print(article["body_md"][:200])`,
        javascript: `const resp = await fetch(
  "${BASE}/api/content/sinal-semanal-48",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const article = await resp.json();
console.log(article.title);
console.log(article.body_md.slice(0, 200));`,
      },
      exampleResponse: `{
  "title": "Sinal Semanal #48",
  "slug": "sinal-semanal-48",
  "content_type": "DATA_REPORT",
  "agent_name": "sintese",
  "confidence_dq": 0.87,
  "body_md": "# Sinal Semanal #48\\n\\n## Destaques...",
  "body_html": "<h1>Sinal Semanal #48</h1>...",
  "published_at": "2026-02-23T10:00:00Z"
}`,
    },
    {
      method: "GET",
      path: "/api/content/newsletter/latest",
      description: "Retorna a newsletter mais recente publicada.",
      params: [],
      responseFields: CONTENT_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/content/newsletter/latest"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/content/newsletter/latest",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
)
latest = resp.json()
print(f"Ultima newsletter: {latest['title']}")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/content/newsletter/latest",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const latest = await resp.json();
console.log(\`Ultima newsletter: \${latest.title}\`);`,
      },
      exampleResponse: `{
  "title": "Sinal Semanal #48",
  "slug": "sinal-semanal-48",
  "content_type": "DATA_REPORT",
  "agent_name": "sintese",
  "confidence_dq": 0.87,
  "published_at": "2026-02-23T10:00:00Z"
}`,
    },
  ],
};

// ---------------------------------------------------------------------------
// Agents API
// ---------------------------------------------------------------------------

const AGENT_SUMMARY_FIELDS: ApiField[] = [
  {
    name: "agent_name",
    type: "string",
    description: "Nome do agente (radar, sintese, codigo, etc.)",
  },
  { name: "last_run", type: "datetime?", description: "Data/hora da última execução" },
  { name: "status", type: "string", description: "Status: running, completed, failed, cancelled" },
  { name: "items_processed", type: "int", description: "Itens processados na última execução" },
  { name: "avg_confidence", type: "float?", description: "Confiança média (0-1)" },
  { name: "sources", type: "int", description: "Número de fontes utilizadas" },
  { name: "error_count", type: "int", description: "Erros na última execução" },
];

const AGENT_RUN_FIELDS: ApiField[] = [
  { name: "id", type: "UUID", description: "Identificador único da execução" },
  { name: "agent_name", type: "string", description: "Nome do agente" },
  { name: "run_id", type: "string", description: "ID único da execução" },
  { name: "status", type: "string", description: "Status: running, completed, failed, cancelled" },
  { name: "started_at", type: "datetime", description: "Início da execução" },
  { name: "completed_at", type: "datetime?", description: "Fim da execução" },
  { name: "items_collected", type: "int?", description: "Itens coletados" },
  { name: "items_processed", type: "int?", description: "Itens processados" },
  { name: "avg_confidence", type: "float?", description: "Confiança média" },
  { name: "error_count", type: "int", description: "Número de erros" },
];

const agentsApi: ApiGroup = {
  id: "agentes",
  name: "Agentes",
  label: "API DE AGENTES",
  description:
    "Status e métricas dos AI agents — execuções, itens processados, confiança e fontes.",
  color: "#59B4FF",
  fieldCount: "10 campos",
  endpoints: [
    {
      method: "GET",
      path: "/api/agents/summary",
      description: "Resumo da última execução de cada agente ativo.",
      params: [],
      responseFields: AGENT_SUMMARY_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/agents/summary"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/agents/summary",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
)
for agent in resp.json():
    print(f"{agent['agent_name']}: {agent['status']} "
          f"({agent['items_processed']} itens)")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/agents/summary",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const agents = await resp.json();
agents.forEach(a =>
  console.log(\`\${a.agent_name}: \${a.status} (\${a.items_processed} itens)\`)
);`,
      },
      exampleResponse: `[
  {
    "agent_name": "radar",
    "last_run": "2026-02-23T08:00:00Z",
    "status": "completed",
    "items_processed": 438,
    "avg_confidence": 0.82,
    "sources": 27,
    "error_count": 0
  },
  {
    "agent_name": "sintese",
    "last_run": "2026-02-23T10:00:00Z",
    "status": "completed",
    "items_processed": 156,
    "avg_confidence": 0.87,
    "sources": 14,
    "error_count": 0
  }
]`,
    },
    {
      method: "GET",
      path: "/api/agents/runs",
      description: "Histórico de execuções dos agentes com filtros.",
      params: [
        { name: "agent_name", type: "string", required: false, description: "Filtra por agente" },
        {
          name: "status",
          type: "string",
          required: false,
          description: "Filtra por status (running, completed, failed)",
        },
        ...PAGINATION_PARAMS,
      ],
      responseFields: AGENT_RUN_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/agents/runs?agent_name=radar&limit=3"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/agents/runs",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"agent_name": "radar", "limit": 3},
)
for run in resp.json():
    print(f"Run {run['run_id']}: {run['status']}")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/agents/runs?agent_name=radar&limit=3",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const runs = await resp.json();
runs.forEach(r =>
  console.log(\`Run \${r.run_id}: \${r.status}\`)
);`,
      },
      exampleResponse: `[
  {
    "id": "a1b2c3d4-...",
    "agent_name": "radar",
    "run_id": "radar-2026-02-23-08",
    "status": "completed",
    "started_at": "2026-02-23T08:00:00Z",
    "completed_at": "2026-02-23T08:12:34Z",
    "items_collected": 512,
    "items_processed": 438,
    "avg_confidence": 0.82,
    "error_count": 0
  }
]`,
    },
  ],
};

// ---------------------------------------------------------------------------
// Funding API (coming soon)
// ---------------------------------------------------------------------------

const fundingApi: ApiGroup = {
  id: "investimentos",
  name: "Investimentos",
  label: "API DE INVESTIMENTOS",
  description: "Rodadas de investimento LATAM com dados verificados de multiplas fontes.",
  color: "#FF8A59",
  fieldCount: "8+ campos",
  comingSoon: true,
  endpoints: [
    {
      method: "GET",
      path: "/api/funding",
      description: "Lista rodadas de investimento com filtros por país, estágio e valor.",
      params: [
        { name: "country", type: "string", required: false, description: "Filtra por país" },
        {
          name: "stage",
          type: "string",
          required: false,
          description: "Estágio (Seed, Series A, B, C, etc.)",
        },
        { name: "min_amount", type: "int", required: false, description: "Valor mínimo em USD" },
        ...PAGINATION_PARAMS,
      ],
      responseFields: [
        { name: "company", type: "string", description: "Nome da empresa" },
        { name: "company_slug", type: "string", description: "Slug da empresa" },
        { name: "country", type: "string", description: "País" },
        { name: "stage", type: "string", description: "Estágio da rodada" },
        { name: "amount_usd", type: "int", description: "Valor em USD" },
        { name: "lead_investors", type: "string[]", description: "Investidores líderes" },
        { name: "announced_at", type: "date", description: "Data do anúncio" },
        { name: "source_url", type: "string", description: "URL da fonte" },
      ],
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/funding?country=Brazil&stage=Series+A"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/funding",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"country": "Brazil", "stage": "Series A"},
)
for deal in resp.json()["items"]:
    print(f"{deal['company']}: \${deal['amount_usd']:,}")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/funding?country=Brazil&stage=Series+A",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const data = await resp.json();
data.items.forEach(deal =>
  console.log(\`\${deal.company}: $\${deal.amount_usd.toLocaleString()}\`)
);`,
      },
      exampleResponse: `{
  "items": [
    {
      "company": "Clip",
      "company_slug": "clip",
      "country": "Mexico",
      "stage": "Series D",
      "amount_usd": 50000000,
      "lead_investors": ["SoftBank", "Viking Global"],
      "announced_at": "2026-01-15",
      "source_url": "https://techcrunch.com/..."
    }
  ],
  "total": 234,
  "limit": 20,
  "offset": 0
}`,
    },
  ],
};

// ---------------------------------------------------------------------------
// Signals API
// ---------------------------------------------------------------------------

const SIGNAL_FIELDS: ApiField[] = [
  { name: "id", type: "UUID", description: "Identificador único" },
  { name: "platform", type: "string", description: "Plataforma (twitter, reddit, bluesky, rss)" },
  { name: "post_url", type: "string", description: "URL do post original" },
  { name: "author_handle", type: "string", description: "Handle do autor" },
  { name: "author_display_name", type: "string", description: "Nome de exibição do autor" },
  { name: "text", type: "string", description: "Texto do post" },
  { name: "published_at", type: "datetime", description: "Data de publicação" },
  { name: "metrics", type: "object", description: "Engajamento: likes, replies, reposts" },
  { name: "theme", type: "string", description: "Tema principal (AI, Fintech, AI in Banking)" },
  { name: "sub_theme", type: "string?", description: "Sub-tema" },
  { name: "sentiment", type: "float", description: "Sentimento: -1 (negativo) a 1 (positivo)" },
  { name: "authority_score", type: "float", description: "Score de autoridade do autor (0-1)" },
];

const CLUSTER_FIELDS: ApiField[] = [
  { name: "id", type: "UUID", description: "Identificador único" },
  { name: "name", type: "string", description: "Nome do cluster de tendencia" },
  { name: "slug", type: "string", description: "Slug URL-friendly" },
  { name: "theme", type: "string", description: "Tema principal" },
  { name: "sub_theme", type: "string?", description: "Sub-tema" },
  { name: "description", type: "string", description: "Descricao do cluster" },
  { name: "signal_count", type: "int", description: "Numero de sinais no cluster" },
  { name: "composite_score", type: "float", description: "Score composto (0-1)" },
  {
    name: "narrative_stage",
    type: "string",
    description: "Estagio narrativo: emerging, accelerating, peaking, declining",
  },
  {
    name: "top_voices",
    type: "object[]",
    description: "Principais vozes: handle, name, authority",
  },
  { name: "top_posts", type: "object[]", description: "Posts mais relevantes" },
  { name: "week_number", type: "int", description: "Semana do ano" },
  { name: "year", type: "int", description: "Ano" },
  {
    name: "first_mover",
    type: "object?",
    description: "Quem postou primeiro: handle, name, posted_at",
  },
];

const VOICE_FIELDS: ApiField[] = [
  { name: "id", type: "UUID", description: "Identificador único" },
  { name: "platform", type: "string", description: "Plataforma monitorada" },
  { name: "handle", type: "string", description: "Handle da conta" },
  { name: "display_name", type: "string?", description: "Nome de exibicao" },
  {
    name: "account_type",
    type: "string?",
    description: "Tipo: founder, vc, executive, thought_leader, company",
  },
  { name: "authority_score", type: "float", description: "Score de autoridade (0-1)" },
  { name: "follower_count", type: "int?", description: "Numero de seguidores" },
  { name: "bio", type: "string?", description: "Biografia" },
  { name: "profile_url", type: "string?", description: "URL do perfil" },
  { name: "sector_tags", type: "string[]?", description: "Tags de setor" },
  { name: "is_active", type: "boolean", description: "Conta ativa no monitoramento" },
];

const PULSE_FIELDS: ApiField[] = [
  { name: "id", type: "UUID", description: "Identificador único" },
  { name: "week_number", type: "int", description: "Semana do ano" },
  { name: "year", type: "int", description: "Ano" },
  { name: "slug", type: "string", description: "Slug URL-friendly (ex: pulse-2026-w08)" },
  {
    name: "accelerating_themes",
    type: "object[]?",
    description: "Temas acelerando: name, score, delta",
  },
  {
    name: "emerging_signals",
    type: "object[]?",
    description: "Sinais emergentes: name, score, platforms",
  },
  { name: "top_posts", type: "object[]?", description: "Posts mais relevantes da semana" },
  { name: "top_voices", type: "object[]?", description: "Vozes mais ativas da semana" },
  { name: "status", type: "string", description: "Status: draft, published" },
];

const SIGNAL_STATS_FIELDS: ApiField[] = [
  { name: "total_signals", type: "int", description: "Total de sinais coletados" },
  { name: "total_clusters", type: "int", description: "Total de clusters ativos" },
  { name: "total_voices", type: "int", description: "Total de vozes monitoradas" },
  {
    name: "platforms",
    type: "object",
    description: "Contagem por plataforma: { twitter: N, ... }",
  },
  { name: "themes", type: "object", description: "Contagem por tema: { AI: N, Fintech: N, ... }" },
];

const CURATED_FEED_FIELDS: ApiField[] = [
  { name: "id", type: "UUID", description: "Identificador único" },
  { name: "editorial_headline", type: "string", description: "Título editorial em pt-BR" },
  {
    name: "editorial_context",
    type: "string?",
    description: "Contexto editorial: por que isso importa",
  },
  { name: "relevance_score", type: "int", description: "Score de relevância (0-100)" },
  { name: "category", type: "string", description: "Categoria: AI, Fintech, Banking, Startup" },
  { name: "original_text", type: "string?", description: "Texto original truncado" },
  { name: "original_url", type: "string?", description: "URL do post original" },
  { name: "platform", type: "string?", description: "Plataforma de origem" },
  { name: "author_handle", type: "string?", description: "Handle do autor" },
  { name: "thumbnail_url", type: "string?", description: "URL da imagem og:image" },
  {
    name: "video_embed",
    type: "object?",
    description: "Embed de vídeo: { platform, embed_url, thumbnail }",
  },
  { name: "theme", type: "string?", description: "Tema (mapeado da categoria)" },
  { name: "curated_at", type: "datetime?", description: "Data da curadoria" },
];

const signalsApi: ApiGroup = {
  id: "sinais",
  name: "Sinais",
  label: "API DE SINAIS",
  description:
    "Social signals coletados pelo agente RADAR — posts, clusters de tendencias, vozes influentes e o pulse semanal.",
  color: "#B59FFF",
  fieldCount: "12 campos por sinal",
  endpoints: [
    {
      method: "GET",
      path: "/api/signals",
      description: "Lista sinais coletados com filtros opcionais e paginacao.",
      params: [
        {
          name: "platform",
          type: "string",
          required: false,
          description: "Filtra por plataforma (twitter, reddit, bluesky, rss)",
        },
        {
          name: "theme",
          type: "string",
          required: false,
          description: "Filtra por tema (AI, Fintech, AI in Banking)",
        },
        ...PAGINATION_PARAMS,
      ],
      responseFields: SIGNAL_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/signals?theme=AI&limit=5"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/signals",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"theme": "AI", "limit": 5},
)
data = resp.json()
for signal in data["items"]:
    print(signal["author_handle"], "-", signal["text"][:80])`,
        javascript: `const resp = await fetch(
  "${BASE}/api/signals?theme=AI&limit=5",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const data = await resp.json();
data.items.forEach(s =>
  console.log(s.author_handle, "-", s.text.slice(0, 80))
);`,
      },
      exampleResponse: `{
  "items": [
    {
      "id": "a1b2c3d4-...",
      "platform": "twitter",
      "author_handle": "karpathy",
      "text": "The most important AI trend right now is...",
      "published_at": "2026-02-23T09:15:00Z",
      "metrics": { "likes": 4200, "reposts": 980, "replies": 210 },
      "theme": "AI",
      "sentiment": 0.72,
      "authority_score": 0.94
    }
  ],
  "total": 12483,
  "limit": 5,
  "offset": 0
}`,
    },
    {
      method: "GET",
      path: "/api/signals/feed",
      description:
        "Lista itens do Feed Curado — sinais com headline editorial, contexto e mídia, ordenados por relevância.",
      params: [
        {
          name: "theme",
          type: "string",
          required: false,
          description: "Filtra por categoria (AI, Fintech, Banking, Startup). Alias: category",
        },
        ...PAGINATION_PARAMS,
      ],
      responseFields: CURATED_FEED_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/signals/feed?theme=AI&limit=10"`,
        python: `import requests

r = requests.get(
    "${BASE}/api/signals/feed",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"theme": "AI", "limit": 10},
)
items = r.json()["items"]
for item in items:
    print(item["relevance_score"], "-", item["editorial_headline"])`,
        javascript: `const res = await fetch(
  "${BASE}/api/signals/feed?theme=AI&limit=10",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const { items } = await res.json();
items.forEach(item =>
  console.log(item.relevance_score, "-", item.editorial_headline)
);`,
      },
      exampleResponse: `{
  "items": [
    {
      "id": "b134...",
      "editorial_headline": "Mega-IPOs de SpaceX, OpenAI e Anthropic vão testar o mercado",
      "editorial_context": "A possível onda de IPOs pode redefinir valuations...",
      "relevance_score": 88,
      "category": "AI",
      "platform": "web",
      "original_url": "https://www.newcomer.co/p/mega-ipos",
      "thumbnail_url": "https://substackcdn.com/image/...",
      "video_embed": null,
      "curated_at": "2026-04-05T11:49:55Z"
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}`,
    },
    {
      method: "GET",
      path: "/api/signals/clusters",
      description: "Lista clusters de tendencias detectados pelo agente RADAR.",
      params: [
        {
          name: "theme",
          type: "string",
          required: false,
          description: "Filtra por tema",
        },
        ...PAGINATION_PARAMS,
      ],
      responseFields: CLUSTER_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/signals/clusters?theme=Fintech&limit=5"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/signals/clusters",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"theme": "Fintech", "limit": 5},
)
for cluster in resp.json()["items"]:
    print(cluster["name"], f"({cluster['narrative_stage']})")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/signals/clusters?theme=Fintech&limit=5",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const data = await resp.json();
data.items.forEach(c =>
  console.log(c.name, \`(\${c.narrative_stage})\`)
);`,
      },
      exampleResponse: `{
  "items": [
    {
      "id": "b2c3d4e5-...",
      "name": "Open Finance no Brasil",
      "slug": "open-finance-brasil",
      "theme": "Fintech",
      "narrative_stage": "accelerating",
      "signal_count": 284,
      "composite_score": 0.78,
      "week_number": 8,
      "year": 2026
    }
  ],
  "total": 47,
  "limit": 5,
  "offset": 0
}`,
    },
    {
      method: "GET",
      path: "/api/signals/clusters/{slug}",
      description: "Retorna o detalhe completo de um cluster pelo slug.",
      params: [{ name: "slug", type: "string", required: true, description: "Slug do cluster" }],
      responseFields: CLUSTER_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/signals/clusters/open-finance-brasil"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/signals/clusters/open-finance-brasil",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
)
cluster = resp.json()
print(cluster["name"], "-", cluster["description"][:100])`,
        javascript: `const resp = await fetch(
  "${BASE}/api/signals/clusters/open-finance-brasil",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const cluster = await resp.json();
console.log(cluster.name, "-", cluster.description.slice(0, 100));`,
      },
      exampleResponse: `{
  "id": "b2c3d4e5-...",
  "name": "Open Finance no Brasil",
  "slug": "open-finance-brasil",
  "theme": "Fintech",
  "sub_theme": "Regulatorio",
  "description": "Discussoes sobre regulamentacao e adocao de open finance...",
  "signal_count": 284,
  "composite_score": 0.78,
  "narrative_stage": "accelerating",
  "top_voices": [{ "handle": "bcboficial", "name": "BCB", "authority": 0.91 }],
  "top_posts": [{ "url": "https://...", "text": "...", "author": "bcboficial", "platform": "twitter" }],
  "week_number": 8,
  "year": 2026,
  "first_mover": { "handle": "fintech_br", "name": "Fintech BR", "posted_at": "2026-02-20T07:30:00Z" }
}`,
    },
    {
      method: "GET",
      path: "/api/signals/pulse",
      description: "Retorna o pulse semanal mais recente publicado.",
      params: [],
      responseFields: PULSE_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/signals/pulse"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/signals/pulse",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
)
pulse = resp.json()
print(f"Semana {pulse['week_number']}/{pulse['year']}")
for theme in pulse.get("accelerating_themes", [])[:3]:
    print(f"  {theme['name']}: {theme['score']:.2f}")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/signals/pulse",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const pulse = await resp.json();
console.log(\`Semana \${pulse.week_number}/\${pulse.year}\`);
pulse.accelerating_themes?.slice(0, 3).forEach(t =>
  console.log(\`  \${t.name}: \${t.score.toFixed(2)}\`)
);`,
      },
      exampleResponse: `{
  "id": "c3d4e5f6-...",
  "week_number": 8,
  "year": 2026,
  "slug": "pulse-2026-w08",
  "accelerating_themes": [
    { "name": "LLM Inference Costs", "score": 0.91, "delta": 0.18 },
    { "name": "Open Finance", "score": 0.78, "delta": 0.12 }
  ],
  "emerging_signals": [
    { "name": "AI Agents em Producao", "score": 0.63, "platforms": ["twitter", "reddit"] }
  ],
  "status": "published"
}`,
    },
    {
      method: "GET",
      path: "/api/signals/voices",
      description: "Lista contas monitoradas pelo agente RADAR, ordenadas por autoridade.",
      params: [
        {
          name: "account_type",
          type: "string",
          required: false,
          description: "Filtra por tipo: founder, vc, executive, thought_leader, company",
        },
        ...PAGINATION_PARAMS,
      ],
      responseFields: VOICE_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/signals/voices?account_type=vc&limit=5"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/signals/voices",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"account_type": "vc", "limit": 5},
)
for voice in resp.json()["items"]:
    print(f"@{voice['handle']} ({voice['account_type']}) - {voice['authority_score']:.2f}")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/signals/voices?account_type=vc&limit=5",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const data = await resp.json();
data.items.forEach(v =>
  console.log(\`@\${v.handle} (\${v.account_type}) - \${v.authority_score.toFixed(2)}\`)
);`,
      },
      exampleResponse: `{
  "items": [
    {
      "id": "d4e5f6a7-...",
      "platform": "twitter",
      "handle": "sequoia",
      "display_name": "Sequoia Capital",
      "account_type": "vc",
      "authority_score": 0.96,
      "follower_count": 850000,
      "sector_tags": ["fintech", "ai", "saas"],
      "is_active": true
    }
  ],
  "total": 312,
  "limit": 5,
  "offset": 0
}`,
    },
    {
      method: "GET",
      path: "/api/signals/stats",
      description: "Retorna estatisticas agregadas do sistema de sinais.",
      params: [],
      responseFields: SIGNAL_STATS_FIELDS,
      examples: {
        curl: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "${BASE}/api/signals/stats"`,
        python: `import requests

resp = requests.get(
    "${BASE}/api/signals/stats",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
)
stats = resp.json()
print(f"{stats['total_signals']:,} sinais, {stats['total_clusters']} clusters")`,
        javascript: `const resp = await fetch(
  "${BASE}/api/signals/stats",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);
const stats = await resp.json();
console.log(\`\${stats.total_signals.toLocaleString()} sinais, \${stats.total_clusters} clusters\`);`,
      },
      exampleResponse: `{
  "total_signals": 12483,
  "total_clusters": 47,
  "total_voices": 312,
  "platforms": {
    "twitter": 7840,
    "reddit": 2910,
    "bluesky": 1200,
    "rss": 533
  },
  "themes": {
    "AI": 6200,
    "Fintech": 4100,
    "AI in Banking": 2183
  }
}`,
    },
  ],
};

// ---------------------------------------------------------------------------
// All API groups
// ---------------------------------------------------------------------------

export const API_GROUPS: ApiGroup[] = [companiesApi, contentApi, agentsApi, signalsApi, fundingApi];

// ---------------------------------------------------------------------------
// Error codes documentation
// ---------------------------------------------------------------------------

export interface ErrorCode {
  code: number;
  name: string;
  description: string;
}

export const ERROR_CODES: ErrorCode[] = [
  { code: 200, name: "OK", description: "Requisição bem-sucedida" },
  { code: 201, name: "Created", description: "Recurso criado com sucesso" },
  { code: 400, name: "Bad Request", description: "Parâmetros inválidos ou faltando" },
  { code: 401, name: "Unauthorized", description: "API key ausente ou inválida" },
  { code: 404, name: "Not Found", description: "Recurso não encontrado" },
  { code: 422, name: "Unprocessable Entity", description: "Erro de validação nos dados enviados" },
  { code: 429, name: "Too Many Requests", description: "Limite de requisições excedido" },
  { code: 500, name: "Internal Server Error", description: "Erro interno do servidor" },
];

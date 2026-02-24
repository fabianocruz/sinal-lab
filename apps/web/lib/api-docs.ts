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
// All API groups
// ---------------------------------------------------------------------------

export const API_GROUPS: ApiGroup[] = [companiesApi, contentApi, agentsApi, fundingApi];

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

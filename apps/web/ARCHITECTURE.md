# ARCHITECTURE.md -- Sinal.lab Frontend

> Atualizado em: 2026-03-06.

---

## Estrutura de Arquivos

```
apps/web/
├── app/
│   ├── layout.tsx                          # Root layout -- SessionProvider, fonts, metadata
│   ├── page.tsx                            # Landing page
│   ├── globals.css                         # Tailwind + global styles
│   ├── sitemap.ts                          # Async sitemap (fetches dynamic slugs from API)
│   ├── (auth)/
│   │   ├── login/page.tsx                  # Login (LoginForm)
│   │   └── cadastro/page.tsx               # Signup (SignupForm)
│   ├── (marketing)/
│   │   ├── marketing.test.tsx
│   │   ├── sobre/page.tsx                  # Institucional
│   │   └── metodologia/page.tsx            # Transparencia editorial
│   ├── api/auth/[...nextauth]/route.ts     # Catch-all NextAuth handler
│   ├── newsletter/
│   │   ├── page.tsx                        # Arquivo de edicoes (SSR + ISR 60s)
│   │   ├── error.tsx                       # Error boundary
│   │   ├── loading.tsx                     # Skeleton
│   │   └── [slug]/
│   │       ├── page.tsx                    # Edicao individual (SSR + ISR 300s)
│   │       ├── opengraph-image.tsx         # OG image dinamica (Edge runtime)
│   │       ├── error.tsx
│   │       └── loading.tsx
│   ├── artigos/
│   │   ├── page.tsx                        # Artigos listing (SSR + ISR 60s)
│   │   ├── artigos.test.tsx                # ArticleContent tests (13 tests)
│   │   └── [slug]/
│   │       └── page.tsx                    # Artigo detail (SSR + ISR 300s)
│   ├── startups/
│   │   └── page.tsx                        # Startup map listing (SSR + ISR 60s)
│   ├── startup/
│   │   └── [slug]/
│   │       └── page.tsx                    # Startup detail + JSON-LD (SSR + ISR 300s)
│   └── conta/
│       └── page.tsx                        # User account page
├── components/
│   ├── Providers.tsx                       # SessionProvider + futuros providers
│   ├── agents/
│   │   ├── AgentAvatar.tsx
│   │   ├── AgentCard.tsx
│   │   ├── AgentTeam.tsx
│   │   └── agents.test.tsx
│   ├── article/
│   │   └── ArticleContent.tsx              # Article detail: hero image, header, gated body
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   ├── SignupForm.tsx
│   │   └── auth.test.tsx
│   ├── layout/
│   │   ├── Navbar.tsx                      # NavbarAuthState + UserMenu dropdown
│   │   ├── Footer.tsx
│   │   ├── Section.tsx
│   │   └── layout.test.tsx
│   ├── newsletter/
│   │   ├── ArchiveCard.tsx                 # Newsletter card with cover image
│   │   ├── NewsletterContent.tsx           # Newsletter detail: gated body
│   │   ├── GatedOverlay.tsx                # Conversion overlay (unauthenticated)
│   │   ├── HeroImage.tsx                   # Reusable hero image (figure + figcaption)
│   │   ├── MarkdownRenderer.tsx            # Markdown -> HTML renderer
│   │   ├── SourcesList.tsx                 # Source links with favicons
│   │   ├── Pagination.tsx                  # Generalized pagination (basePath prop)
│   │   ├── SearchBar.tsx                   # Generalized search (basePath prop)
│   │   ├── gating.test.tsx
│   │   └── newsletter.test.tsx
│   └── startup/
│       ├── CompanyCard.tsx                 # Startup card for listing
│       ├── CompanyDetail.tsx               # Startup detail page content
│       └── SectorFilter.tsx               # URL-based sector filter (Client Component)
├── lib/
│   ├── auth.ts                             # NextAuth config
│   ├── auth.test.ts
│   ├── api.ts                              # API client (newsletters, companies, articles)
│   ├── api.test.ts
│   ├── constants.ts                        # AGENT_PERSONAS, AGENT_COLORS
│   ├── constants.test.ts
│   ├── newsletter.ts                       # Newsletter + ContentApiItem types, CARD_GRADIENTS
│   ├── newsletter.test.ts
│   ├── company.ts                          # Company type + SECTOR_OPTIONS
│   ├── jsonld.ts                           # JSON-LD helpers (companyJsonLd)
│   ├── utils.ts
│   └── utils.test.ts
└── test/
    └── setup.tsx
```

---

## 1. Autenticacao (NextAuth.js v5)

**Estrategia:** JWT stateless. O FastAPI e o dono do banco de usuarios.

### Fluxo

```
Browser -> NextAuth -> CredentialsProvider -> POST /api/auth/verify (FastAPI)
                    -> GoogleProvider       -> OAuth Google
JWT persiste: token.id, token.status
Session expoe: session.user.id, session.user.status
```

### Arquivos-chave

| Arquivo | Responsabilidade |
|---|---|
| `lib/auth.ts` | Config NextAuth: providers, callbacks, paginas customizadas |
| `app/api/auth/[...nextauth]/route.ts` | Catch-all para GET/POST do NextAuth |
| `components/Providers.tsx` | `<SessionProvider>` no root layout |
| `components/auth/LoginForm.tsx` | `signIn("credentials", ...)` |
| `components/auth/SignupForm.tsx` | POST `/api/users` no FastAPI, depois `signIn` |

### Callbacks JWT

```typescript
// jwt: persiste campos customizados no token
token.id     = user.id
token.status = user.status ?? "active"

// session: expoe no cliente
session.user.id     = token.id
session.user.status = token.status
```

### Variaveis de Ambiente

| Variavel | Uso |
|---|---|
| `NEXTAUTH_SECRET` | Assina os tokens JWT |
| `NEXTAUTH_URL` | URL base para callbacks OAuth |
| `GOOGLE_CLIENT_ID` | OAuth Google |
| `GOOGLE_CLIENT_SECRET` | OAuth Google |
| `NEXT_PUBLIC_API_URL` | Base URL do FastAPI (default: `http://localhost:8000`) |

---

## 2. Content Gating

**Abordagem:** client-side only. Todo o HTML e renderizado no servidor (SSR); a divisao visivel/oculta ocorre no cliente via `useSession()`.

### Logica de split

```typescript
// NewsletterContent.tsx / ArticleContent.tsx
const blocks     = body.split("\n\n").filter(p => p.trim().length > 0);
const previewCount = Math.ceil(blocks.length * 0.3);  // ~30% visivel
const previewMd    = blocks.slice(0, previewCount);    // sempre renderizado
const gatedMd      = blocks.slice(previewCount);        // condicional
```

### Estados de renderizacao

| Status da sessao | Conteudo exibido |
|---|---|
| `"loading"` | Apenas preview (30%), sem overlay |
| `"unauthenticated"` | Preview + `<GatedOverlay>` |
| `"authenticated"` | Conteudo completo + sources + footer links |

Usado em: `NewsletterContent.tsx` (newsletters) e `ArticleContent.tsx` (artigos).

---

## 3. Cover Images

### Newsletter Cards (ArchiveCard.tsx)

Cards exibem cover image do `metadata.hero_image.url` sobre gradiente CSS fallback:

```tsx
{newsletter.metadata?.hero_image?.url && (
  <img src={newsletter.metadata.hero_image.url} alt="" className="..." />
)}
```

Gradientes definidos em `lib/newsletter.ts` (`CARD_GRADIENTS`): 6 variacoes com cores dos agentes.

### Article Cards (artigos/page.tsx)

Mesmo pattern dos newsletter cards, mas com `metadata_?.hero_image?.url` (note o underscore do campo da API).

### Detail Pages

Ambos usam o componente `HeroImage` para exibir a imagem hero com caption e credit:

```tsx
<HeroImage hero_image={item.metadata_?.hero_image} agentColor={ACCENT_COLOR} />
```

### Pipeline de geracao

Covers sao geradas pelo pipeline em `apps/agents/covers/`:
1. LLM (Claude Sonnet) gera prompt de imagem baseado no conteudo
2. Recraft V3 gera imagem (realistic_image, 1820x1024)
3. Pillow aplica overlay (badge, gradiente, barra de cores)
4. Resize para 1200x628 (OG standard)
5. Upload para Vercel Blob
6. `metadata.hero_image` atualizado no banco

---

## 4. Paginas de Conteudo

### /newsletter (arquivo)

Server Component. Busca via `fetchNewsletters()`. Grid 3 colunas com `ArchiveCard`. Pagination generalizada com `basePath="/newsletter"`.

### /newsletter/[slug] (detalhe)

Server Component que busca `fetchNewsletterBySlug()`. Renderiza `NewsletterContent` (Client Component) com gating.

### /artigos (listing)

Server Component. Busca via `fetchArticles()`. Grid 3 colunas com cards inline (mesma pattern de ArchiveCard mas com author info e badge "ARTIGO").

### /artigos/[slug] (detalhe)

Server Component que busca o artigo. Renderiza `ArticleContent` (Client Component) com:
- Hero image via `HeroImage`
- Badge "Artigo" + data formatada
- Author info (nome + "Autor" ou "Sinal Editorial" + "Redacao")
- Corpo markdown via `MarkdownRenderer`
- Gating (30% preview / full para autenticados)

### /startups (mapa)

Server Component com `searchParams` para filtros. Busca via `fetchCompanies()`. Grid com `CompanyCard`. Filtros: sector, country, search. Pagination com `basePath="/startups"`.

### /startup/[slug] (detalhe)

Server Component com `CompanyDetail`. JSON-LD Organization (schema.org) via `companyJsonLd()`. 22 campos do banco.

---

## 5. Componentes de Agentes

Dados de persona centralizados em `lib/constants.ts` (`AGENT_PERSONAS`).

| Componente | Descricao | Props |
|---|---|---|
| `AgentAvatar` | Avatar circular com iniciais + cor | `agentKey`, `size` |
| `AgentCard` | Card completo: avatar, nome, cargo, badge, descricao | `agentKey` |
| `AgentTeam` | Grid com os 5 agentes | nenhuma |

### AGENT_PERSONAS (lib/constants.ts)

```
sintese  -> Clara Medeiros   -> #E8FF59
radar    -> Tomas Aguirre    -> #59FFB4
codigo   -> Marina Costa     -> #59B4FF
funding  -> Rafael Oliveira  -> #FF8A59
mercado  -> Valentina Rojas  -> #C459FF
```

---

## 6. Componentes Reutilizaveis

| Componente | Prop-chave | Usado em |
|---|---|---|
| `Pagination` | `basePath` (default: `/newsletter`) | /newsletter, /artigos, /startups |
| `SearchBar` | `basePath` (default: `/newsletter`) | /newsletter, /startups |
| `SectorFilter` | usa `useSearchParams`/`useRouter` | /startups |
| `HeroImage` | `hero_image`, `agentColor` | newsletter detail, article detail |
| `MarkdownRenderer` | `content`, `agentColor` | newsletter detail, article detail |
| `GatedOverlay` | nenhuma | newsletter detail, article detail |
| `SourcesList` | `sources`, `agentColor` | newsletter detail, article detail |

---

## 7. OG Image Dinamica

**Arquivo:** `app/newsletter/[slug]/opengraph-image.tsx`

**Runtime:** Edge (Vercel Edge Network). Usa `ImageResponse` do `next/og`.

- Tamanho: 1200 x 630 px
- Elementos: logo Sinal, badge do agente com cor, titulo, linha de edicao/data, barra de gradiente
- Fallback para slugs desconhecidos: branding generico Sinal

---

## 8. Error Boundaries e Loading States

Todas as rotas data-fetching tem `error.tsx` e `loading.tsx` co-localizados.

| Rota | error.tsx | loading.tsx |
|---|---|---|
| `/newsletter` | "Algo deu errado" + retry/home | Header skeleton + 6 pills + featured card + 6 cards |
| `/newsletter/[slug]` | "Algo deu errado" + retry/arquivo | Back link + header + avatar + 5 linhas |

---

## 9. SEO

- Metadata (title, description, OG tags) em todas as paginas
- JSON-LD Organization em `/startup/[slug]` via `companyJsonLd()`
- Sitemap async (`app/sitemap.ts`) com slugs dinamicos de newsletters, artigos, e companies
- Paginas programaticas com min 300 palavras unicas

---

## Cobertura de Testes

**Total:** 998 testes frontend (Vitest + Testing Library).

| Area | Arquivo de teste | Status |
|---|---|---|
| Componentes de agentes | `components/agents/agents.test.tsx` | testado |
| Auth (LoginForm, SignupForm) | `components/auth/auth.test.tsx` | testado |
| Gating (NewsletterContent, GatedOverlay) | `components/newsletter/gating.test.tsx` | testado |
| Newsletter components | `components/newsletter/newsletter.test.tsx` | testado |
| Article components | `app/artigos/artigos.test.tsx` | testado (13 tests) |
| Layout (Navbar, Footer, Section) | `components/layout/layout.test.tsx` | testado |
| Landing components | `components/landing/landing.test.tsx` | testado |
| Paginas marketing | `app/(marketing)/marketing.test.tsx` | testado |
| lib/auth config | `lib/auth.test.ts` | testado |
| lib/constants | `lib/constants.test.ts` | testado |
| lib/newsletter | `lib/newsletter.test.ts` | testado |
| lib/api | `lib/api.test.ts` | testado |
| lib/utils | `lib/utils.test.ts` | testado |
| OG image | -- | nao testavel (Edge runtime) |

---

## Dependencias Externas

| Pacote | Uso |
|---|---|
| `next-auth` (v5 beta) | Autenticacao (JWT, OAuth) |
| `lucide-react` | Icones |
| `class-variance-authority` | Variantes de estilo tipadas |
| `clsx` + `tailwind-merge` | Merge de classes CSS |

# ARCHITECTURE.md — Sinal.lab Frontend (Fase 3)

> Documentacao dos subsistemas adicionados na Fase 3. Atualizado em: 2026-02-20.

---

## Estrutura de Arquivos

```
apps/web/
├── app/
│   ├── layout.tsx                          # Root layout — monta SessionProvider
│   ├── page.tsx                            # Landing page
│   ├── (auth)/
│   │   ├── login/page.tsx                  # Pagina de login (LoginForm)
│   │   └── cadastro/page.tsx               # Pagina de cadastro (SignupForm)
│   ├── (marketing)/
│   │   ├── marketing.test.tsx
│   │   ├── sobre/page.tsx                  # Pagina institucional
│   │   └── metodologia/page.tsx            # Transparencia editorial
│   ├── api/auth/[...nextauth]/route.ts     # Catch-all NextAuth handler
│   └── newsletter/
│       ├── page.tsx                        # Arquivo de edicoes
│       ├── error.tsx                       # Error boundary do arquivo
│       ├── loading.tsx                     # Skeleton do arquivo
│       └── [slug]/
│           ├── page.tsx                    # Edicao individual
│           ├── opengraph-image.tsx         # OG image dinamica (Edge runtime)
│           ├── error.tsx                   # Error boundary do slug
│           └── loading.tsx                 # Skeleton do slug
├── components/
│   ├── Providers.tsx                       # SessionProvider + futuros providers
│   ├── agents/
│   │   ├── AgentAvatar.tsx
│   │   ├── AgentCard.tsx
│   │   ├── AgentTeam.tsx
│   │   └── agents.test.tsx
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   ├── SignupForm.tsx
│   │   └── auth.test.tsx
│   ├── layout/
│   │   ├── Navbar.tsx                      # Inclui NavbarAuthState
│   │   ├── Footer.tsx
│   │   ├── Section.tsx
│   │   └── layout.test.tsx
│   └── newsletter/
│       ├── NewsletterContent.tsx           # Gating client-side
│       ├── GatedOverlay.tsx                # Overlay de conversao
│       ├── gating.test.tsx
│       └── newsletter.test.tsx
├── lib/
│   ├── auth.ts                             # NextAuth config
│   ├── auth.test.ts
│   ├── constants.ts                        # AGENT_PERSONAS, AGENT_COLORS
│   ├── constants.test.ts
│   ├── newsletter.ts
│   ├── newsletter.test.ts
│   ├── api.ts
│   ├── api.test.ts
│   ├── utils.ts
│   └── utils.test.ts
└── test/
    └── setup.tsx
```

---

## 1. Autenticacao (NextAuth.js v5)

**Estrategia:** JWT stateless — sem adapter de banco no Next.js. O FastAPI e o dono do banco de usuarios.

### Fluxo

```
Browser → NextAuth → CredentialsProvider → POST /api/auth/verify (FastAPI)
                   → GoogleProvider       → OAuth Google
JWT persiste: token.id, token.status
Session expoe: session.user.id, session.user.status
```

### Arquivos-chave

| Arquivo | Responsabilidade |
|---|---|
| `lib/auth.ts` | Config NextAuth — providers, callbacks, paginas customizadas |
| `app/api/auth/[...nextauth]/route.ts` | Catch-all para GET/POST do NextAuth |
| `components/Providers.tsx` | Monta `<SessionProvider>` no root layout |
| `components/auth/LoginForm.tsx` | Chama `signIn("credentials", ...)` |
| `components/auth/SignupForm.tsx` | POST `/api/users` no FastAPI, depois `signIn` |

### Callbacks JWT

```typescript
// jwt: persiste campos customizados no token
token.id     = user.id
token.status = user.status ?? "active"   // Google sign-ins: default "active"

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
// NewsletterContent.tsx
const paragraphs    = newsletter.body.split("\n\n").filter(p => p.trim().length > 0);
const previewCount  = Math.ceil(paragraphs.length * 0.3);  // ~30% visivel
const preview       = paragraphs.slice(0, previewCount);   // sempre renderizado
const gated         = paragraphs.slice(previewCount);       // condicional
```

### Estados de renderizacao

| Status da sessao | Conteudo exibido |
|---|---|
| `"loading"` | Apenas preview (30%) — sem overlay |
| `"unauthenticated"` | Preview + `<GatedOverlay>` |
| `"authenticated"` | Conteudo completo |

### GatedOverlay

Componente `components/newsletter/GatedOverlay.tsx`:
- Gradiente fade de 100px sobrepondo o ultimo paragrafo visivel
- Card com CTA: "Criar conta gratuita" (`/cadastro`) e "Ja tenho conta" (`/login`)

**Limitacao conhecida:** o gating e bypassavel via JavaScript desabilitado ou ferramentas de dev. Gating server-side esta planejado para versao futura (requer middleware + sessao validada no servidor).

---

## 3. OG Image Dinamica

**Arquivo:** `app/newsletter/[slug]/opengraph-image.tsx`

**Runtime:** Edge (Vercel Edge Network). Usa `ImageResponse` do `next/og` (motor Satori).

### Dimensoes e conteudo

- Tamanho: 1200 x 630 px
- Elementos renderizados: logo Sinal, badge do agente com cor, titulo (max 3 linhas via `-webkit-line-clamp`), linha de edicao/data, barra de gradiente com as 5 cores dos agentes
- Fallback para slugs desconhecidos: branding generico Sinal + tagline

### Limitacoes

- Fontes: sistema apenas (Georgia, monospace) — sem carregamento de fontes customizadas
- Nao testavel com jsdom — `ImageResponse` usa APIs exclusivas do Edge runtime. Verificacao feita via `next build`

---

## 4. Componentes de Agentes

Dados de persona centralizados em `lib/constants.ts` (`AGENT_PERSONAS`). Todos os componentes consomem esse Record — sem duplicacao de dados de cor ou nome.

### Componentes

| Componente | Descricao | Props principais |
|---|---|---|
| `AgentAvatar` | Avatar circular com iniciais, cor do agente | `agentKey`, `size: "sm" \| "md" \| "lg"` |
| `AgentCard` | Card completo com avatar, nome, cargo, badge, descricao | `agentKey` |
| `AgentTeam` | Grid com os 5 agentes — renderiza `AgentCard` para cada key | nenhuma |

### AGENT_PERSONAS (lib/constants.ts)

```typescript
// 5 agentes, cada um com: name, role, agentCode, color (hex), description, avatarPath
sintese  → Clara Medeiros   → #E8FF59
radar    → Tomas Aguirre    → #59FFB4
codigo   → Marina Costa     → #59B4FF
funding  → Rafael Oliveira  → #FF8A59
mercado  → Valentina Rojas  → #C459FF
```

---

## 5. Paginas Internas de Marketing

Ambas sao Server Components puros (sem `"use client"`), com metadata SSR e rota dentro do route group `(marketing)`.

### /sobre

4 secoes usando o wrapper `<Section label="...">`:

1. **SOBRE** — definicao da plataforma
2. **MISSAO** — proposta de valor e diferenciais
3. **COMO FUNCIONA** — grid 3 cards (pesquisa → filtragem → revisao humana)
4. **OS AGENTES** — grid iterando sobre `Object.values(AGENT_PERSONAS)`

### /metodologia

4 secoes:

1. **METODOLOGIA** — introducao ao pipeline
2. **PIPELINE** — 6 steps em grid (Coleta → Processamento → Validacao → Filtragem → Sintese → Revisao)
3. **SCORE DE QUALIDADE** — DQ grades A/B/C/D com cor de agente correspondente
4. **TRANSPARENCIA** — links para GitHub e Log de Correcoes

---

## 6. Estado de Autenticacao na Navbar

**Subcomponente:** `NavbarAuthState` (dentro de `Navbar.tsx`, nao exportado separadamente).

Usa `useSession()` — por isso `Navbar.tsx` e `"use client"`.

| Estado (`status`) | Desktop | Mobile |
|---|---|---|
| `"loading"` | `<span>` vazio 8x8 (evita layout shift) | idem |
| `"authenticated"` | Circulo com inicial do usuario → `/newsletter` | Item "Minha conta" com circulo + label |
| `"unauthenticated"` | Link "Entrar" → `/login` | Link "Entrar" |

---

## 7. Error Boundaries e Loading States

Todas as rotas data-fetching tem `error.tsx` e `loading.tsx` co-localizados.

| Rota | error.tsx | loading.tsx |
|---|---|---|
| `/newsletter` | "Algo deu errado" + botoes retry/home | Header skeleton + 6 pills + featured card + 6 cards |
| `/newsletter/[slug]` | "Algo deu errado" + botoes retry/arquivo | Back link + header + avatar + 5 linhas de corpo |

Todos os `error.tsx` sao `"use client"` (exigencia do Next.js para receber a prop `reset`).

---

## Cobertura de Testes

**Total:** 580+ testes em 12+ arquivos.

| Area | Arquivo de teste | Status |
|---|---|---|
| Componentes de agentes | `components/agents/agents.test.tsx` | testado |
| Auth (LoginForm, SignupForm) | `components/auth/auth.test.tsx` | testado |
| Gating (NewsletterContent, GatedOverlay) | `components/newsletter/gating.test.tsx` | testado |
| Newsletter components | `components/newsletter/newsletter.test.tsx` | testado |
| Layout (Navbar, Footer, Section) | `components/layout/layout.test.tsx` | testado |
| Landing components | `components/landing/landing.test.tsx` | testado |
| Paginas marketing | `app/(marketing)/marketing.test.tsx` | testado |
| lib/auth config | `lib/auth.test.ts` | testado |
| lib/constants | `lib/constants.test.ts` | testado |
| lib/newsletter | `lib/newsletter.test.ts` | testado |
| lib/api | `lib/api.test.ts` | testado |
| lib/utils | `lib/utils.test.ts` | testado |
| OG image (`opengraph-image.tsx`) | — | **nao testavel** (Edge runtime) |

**O que nao e testavel:** `app/newsletter/[slug]/opengraph-image.tsx` usa `ImageResponse` do Edge runtime, incompativel com jsdom. Verificado apenas via `next build`.

---

## Dependencias Externas (Fase 3)

| Pacote | Versao | Uso |
|---|---|---|
| `next-auth` | `5.0.0-beta.25` | Autenticacao (JWT, OAuth) |
| `lucide-react` | latest | Icones (Menu, X na Navbar) |
| `class-variance-authority` | latest | Variantes de estilo tipadas |
| `clsx` | latest | Condicional de classes CSS |
| `tailwind-merge` | latest | Merge de classes Tailwind sem conflito |

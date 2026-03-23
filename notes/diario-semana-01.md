---
# Metadados para o Admin da Sinal
title: "6 PRs para colocar um site no ar"
subtitle: "Semana 1 do diário de construção — deploy wars, a morte do Beehiiv, e por que trocamos toda a stack de email em uma tarde"
author_name: "Santos de Machine"
content_type: ARTICLE
summary: "Migramos de Vite para Next.js, enfrentamos 6 PRs consecutivos para fazer o Vercel funcionar, matamos o Beehiiv em favor do Resend, construímos um admin content editor, e colocamos a Sinal no ar. Duas plataformas, dez horas de deploy hell, zero downtime."
meta_description: "Diário de construção da Sinal, semana 1. Deploy no Vercel e Railway, migração Beehiiv para Resend, admin editor, content gating — e os 6 PRs consecutivos que foram necessários para colocar um Next.js monorepo no ar."
sources:
  - https://sinal.tech
  - https://github.com/fabianocruz/sinal-lab
  - https://vercel.com
  - https://railway.app
  - https://resend.com
---

Na semana passada terminamos com 5 agentes rodando, 800 testes, e nenhum pixel na tela. Essa semana colocamos a Sinal no ar. Parece um avanço linear. Não foi. Deploy é onde o otimismo de engenharia morre. Cada plataforma tem suas armadilhas, cada integração tem seus edge cases, e o espaço entre "funciona no localhost" e "funciona em produção" é maior do que parece.

## De Vite para Next.js em um commit

O frontend original era uma SPA em Vite. Funcionava. Mas a Sinal precisa de SEO — newsletters indexadas, páginas de agentes rastreáveis, Open Graph tags dinâmicas. SSR não é opcional para um produto de conteúdo. A migração para Next.js 14 com App Router foi uma decisão sem volta.

Migramos tudo: landing page com 12 seções do design system, arquivo de newsletters com busca e filtros, páginas individuais de cada newsletter com rendering de Markdown rico, sistema de auth com registro, login, e sessões. Rotas dinâmicas para cada agente — `/radar/[slug]`, `/funding/[slug]`, `/codigo/[slug]`, `/mercado/[slug]`. Content gating para incentivar cadastro. Cada página com metadata, JSON-LD, e OG images geradas dinamicamente.

O resultado: 540 testes frontend cobrindo componentes, libs, auth, e SEO. É mais teste do que a maioria dos projetos tem no frontend inteiro. A razão é prática — com 5 agentes produzindo conteúdo dinâmico, qualquer regressão no rendering afeta dezenas de páginas. Testes são a rede de segurança.

## A guerra do Vercel

Colocar um monorepo Next.js no Vercel deveria ser trivial. Não foi.

PR #11: o primeiro deploy falhou porque o `vercel.json` tinha um `ignoreCommand` que bloqueava tudo. Removemos. PR #12: o Vercel não encontrava o pnpm. Adicionamos `packageManager` ao `package.json`. PR #13: o engine do Node não batia. Adicionamos `.npmrc` com `engine-strict=false`. Aí descobrimos que um `package-lock.json` órfão fazia o Vercel usar npm em vez de pnpm. Removemos. O `build` usava `cd apps/web && next build` — que não funcionava no Vercel porque o monorepo precisa de `pnpm --filter @sinal/web build`. Corrigimos. O `outputDirectory` estava duplicado. Corrigimos.

Seis PRs consecutivos. Cada uma resolvendo um problema que o anterior revelava. É frustrante, mas é a realidade de deploy em plataformas managed: a documentação cobre o caminho feliz, e cada monorepo tem suas particularidades que só aparecem no push.

Depois do deploy funcionar, ainda tinham os bugs visuais que só aparecem em produção. O glow do background do hero era invisível — a opacidade de 0.02 que funcionava no dev era arredondada para zero pelo build otimizado. Subimos para 0.04. O hero não ocupava a viewport inteira em Safari mobile — `min-h-screen` não considera a barra de navegação. Trocamos por `min-h-dvh`.

Pequenos detalhes. Nenhum deles visível em desenvolvimento.

## A guerra do Railway

Se o Vercel foi difícil, o Railway foi criativo.

A API da Sinal roda FastAPI em Python. O plano era simples: Dockerfile, build, deploy. O Railway detectou o `package.json` do monorepo e tentou fazer build como se fosse um projeto Node. Configuramos o builder para Dockerfile na UI. O Railway não encontrou o Dockerfile porque estava em `apps/api/`. Movemos para a raiz do repo. O `railway.toml` com `dockerfilePath` foi ignorado — a configuração pela UI é que prevalece. O `PORT` não era injetado pelo Railway em builds via Dockerfile. Adicionamos explicitamente.

Aí veio o banco. A URL interna (`postgres.railway.internal`) funciona entre serviços Railway, mas não funciona para migrations rodadas localmente. Para isso, precisamos da URL pública (`trolley.proxy.rlwy.net`). E o `load_dotenv()` do alembic carregava o `.env` local e sobrescrevia a `DATABASE_URL` que o Railway injetava. Mudamos para `override=False`.

Cada uma dessas correções levou entre 10 minutos e 2 horas para diagnosticar. A documentação do Railway é boa, mas assume que seu projeto é um app simples — não um monorepo Python com frontend Node e banco PostgreSQL no mesmo workspace.

## A morte do Beehiiv

O plano original de distribuição era usar o Beehiiv para newsletters. Construímos um publisher que combinava os outputs dos cinco agentes em HTML formatado e enviava via API. Funcionava.

Mas durante a integração percebemos que o Beehiiv é uma plataforma de newsletter, não uma API de email. A distinção importa. Queríamos controle sobre o template, sobre a audiência, sobre o momento do envio. Queríamos que o cadastro no site sincronizasse com a lista de envio. Queríamos emails transacionais (boas-vindas, confirmação) e broadcasts (newsletter semanal) no mesmo sistema.

Em uma tarde, matamos o Beehiiv e construímos em cima do Resend. Audience service para gerenciar assinantes. Broadcast service para envios em massa. Template unificado em HTML para transacionais e newsletters. Sync automático entre o banco de usuários e a audiência do Resend. Preview CLI para QA visual de emails.

A lição: ferramentas all-in-one economizam tempo no início e custam flexibilidade no final. O Beehiiv resolveria 80% se quiséssemos ser "mais uma newsletter". Mas a Sinal é uma plataforma com newsletter como canal de distribuição — a diferença exige controle sobre a stack de email.

## O admin que não existia

Com a API rodando e o frontend no ar, percebemos um gap: não tínhamos como publicar conteúdo que não fosse gerado por agentes. Artigos de opinião, ensaios do fundador, análises manuais — tudo isso precisava de um editor.

Construímos um admin content editor em um dia. Editor Markdown com preview ao vivo, campos de SEO (meta description com contador de caracteres), gestão de fontes, publicação e edição de artigos. Protegido por sessão com NextAuth. Proxy de API para contornar a autenticação cross-origin entre Next.js e FastAPI.

Junto com o editor, veio a separação entre `/newsletter` (briefings gerados por agentes) e `/artigos` (conteúdo editorial humano). São dois tipos de conteúdo com cadências, tons e propósitos diferentes. A mesma API serve os dois, mas as rotas no frontend são distintas.

## Onde terminou a semana

No final de sexta, a Sinal tinha:

- **sinal.tech** no ar via Vercel (Next.js 14, SSR, SEO)
- **sinalapi-prod.up.railway.app** no ar via Railway (FastAPI, PostgreSQL)
- Auth completo (registro, login, Google OAuth, sessões)
- Newsletter archive com busca, filtros, e content gating
- Admin editor para publicação humana
- Email stack própria via Resend (transacionais + broadcasts)
- Sync automático de audiência
- ~2.000 testes (backend + frontend)
- 28 PRs merged na semana

A Sinal existia como conceito na segunda. Na sexta, tinha URL, tinha usuários, tinha conteúdo publicado. O gap entre as duas é feito de 6 PRs no Vercel, 5 fixes no Railway, uma plataforma de email substituída, e a convicção de que velocidade sem testes é dívida técnica disfarçada de progresso.

---

*Deploy não é a última milha. É a primeira vez que seu código encontra a realidade.*

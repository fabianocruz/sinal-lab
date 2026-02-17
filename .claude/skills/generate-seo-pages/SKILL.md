---
name: generate-seo-pages
description: Gera paginas programaticas SEO a partir dos dados do banco
argument-hint: "[tipo] (startup|investidor|ecossistema|setor|tecnologia|glossario)"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

Gere paginas programaticas do tipo: $ARGUMENTS

Passos:
1. Consulte o banco para listar entidades do tipo $ARGUMENTS
2. Para cada entidade:
   a. Gere conteudo com minimo 300 palavras (contextual, nao template)
   b. Inclua JSON-LD structured data
   c. Gere internal links para paginas relacionadas
   d. Verifique que nao e thin content
3. Crie/atualize os arquivos em apps/web/app/$ARGUMENTS/[slug]/page.tsx
4. Atualize o sitemap
5. Reporte quantas paginas foram geradas/atualizadas

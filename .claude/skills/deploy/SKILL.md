---
name: deploy
description: Deploy da plataforma para producao ou staging
argument-hint: "[ambiente] (staging|production)"
allowed-tools: Bash, Read, Glob, Grep
---

Deploy para: $ARGUMENTS

Passos:
1. Rode todos os testes (pnpm test && pytest)
2. Verifique que nao ha migrations pendentes
3. Build do frontend (pnpm build)
4. Se staging:
   a. Deploy frontend para Vercel preview
   b. Deploy API para AWS staging
5. Se production:
   a. Confirme que staging esta estavel
   b. Deploy frontend para Vercel production
   c. Deploy API para AWS production
   d. Rode smoke tests pos-deploy
6. Reporte status do deploy

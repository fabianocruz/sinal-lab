---
name: run-agent
description: Executa um AI agent da plataforma e exibe resultados
argument-hint: "[nome-do-agent] (radar|funding|mercado|index|codigo|seo|sintese)"
allowed-tools: Bash, Read, Glob, Grep
---

Execute o AI agent: $ARGUMENTS

Passos:
1. Verifique que o agent existe em apps/agents/$ARGUMENTS/
2. Rode o agent: `python -m apps.agents.$ARGUMENTS.main`
3. Exiba o output formatado
4. Mostre o confidence score do resultado
5. Se houver erros, analise os logs em apps/agents/$ARGUMENTS/logs/

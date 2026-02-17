---
name: validate-content
description: Roda o pipeline editorial completo em um conteudo antes de publicar
argument-hint: "[caminho-do-arquivo-de-conteudo]"
allowed-tools: Bash, Read, Glob, Grep
---

Valide o conteudo em: $ARGUMENTS

Pipeline editorial:
1. DATA VALIDATION — Cruze dados citados com fontes. Score: A/B/C/D
2. FACT-CHECK — Verifique consistencia numerica e temporal
3. BIAS DETECTION — Cheque distribuicao geografica, setorial, de estagio
4. SEO CHECK — Verifique title, meta, structured data, internal links
5. CONFIDENCE SCORE — Calcule score composto (DQ + AC)

Para cada etapa, reporte:
- Status: PASS / WARNING / FAIL
- Detalhes dos issues encontrados
- Sugestoes de correcao

Se houver algum FAIL, NAO publique. Liste as correcoes necessarias.

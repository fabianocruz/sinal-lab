---
name: seed-database
description: Popula o banco com dados iniciais de startups, investidores e ecossistemas LATAM
argument-hint: "[tipo] [quantidade] (ex: startups 100)"
allowed-tools: Bash, Read, Write, Glob, Grep
---

Seed do banco de dados: $ARGUMENTS

Passos:
1. Leia o schema em packages/database/
2. Colete dados das fontes publicas configuradas
3. Normalize (moeda para USD, datas ISO, categorizacao por setor)
4. Insira no banco com provenance tracking (fonte, timestamp, metodo)
5. Rode data quality checks
6. Reporte: total inserido, quality scores, cobertura por setor/cidade

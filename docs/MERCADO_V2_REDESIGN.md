# MERCADO v2 Redesign — Market Intelligence Weekly

**Status:** Em execução (2026-04-21)
**Motivação:** MERCADO v1 ("data dump de GitHub orgs") não passa na régua editorial. Output é curiosidade técnica, não análise que CTO/VC pararia de trabalhar pra ler.

## Separação de responsabilidades

### INDEX — "Base de dados viva de empresas LATAM"
- **Escreve em** `companies` table
- **Alimenta** `/startups`
- **Fontes:** GitHub orgs (TODAS cidades LATAM), Receita Federal, YC, CoreSignal, Crunchbase dumps, ABStartups, StartupsLatam, ingests manuais
- **Cron:** segunda + sábado (2x/semana)
- **Não gera newsletter**

### FUNDING — "Capital Flow Tracker" (mantém)
- **Escreve em** `funding_rounds` table
- **Fontes:** RSS (latamlist, crunchbase_manual_dump), SEC Form D
- **Cron:** diário
- **Gera newsletter** de rodadas da semana

### MERCADO v2 — "Market Intelligence Weekly"
- **NÃO escreve em** `companies` nem `funding_rounds`
- **Lê:** `funding_rounds` (semana + histórico 90d), `companies` (updates), RSS setorial
- **Cron:** semanal
- **Gera newsletter editorial** por setor

## Arquitetura MERCADO v2

```
collect()
  ├── funding_rounds: announced_date >= NOW() - 7 days (sinal da semana)
  ├── funding_rounds: announced_date >= NOW() - 90 days (contexto setorial)
  ├── companies: updated_at >= NOW() - 7 days (updates recentes)
  └── RSS setorial: latamlist, neofeed, mobile_time, valor (narrativa)

process()
  ├── classify por setor (Fintech 40%, AI 20%, DevTools 10%, Vertical 15%, Cross 15%)
  ├── cross-reference: funding + news + company em mesmo setor
  └── score: round size, source authority, cross-ref density

output() via LLM writer
  ├── headline editorial (LLM)
  ├── tese da semana (intro LLM, 3-5 frases)
  ├── 4 sections (uma por setor focal)
  │   └── cada section: 2-3 bullets com analysis (LLM)
  ├── 3 callouts (highlights estilo SINTESE)
  └── se sinal fraco → retorna None (não publica)
```

## Fases de execução

### Fase 1 — Preparação (sem quebra)
- [x] Doc do plano (este arquivo)
- [ ] Despublicar `mercado-week-17` v1 de /newsletter

### Fase 2 — Migração GitHub collector para INDEX
- [ ] Mover config das 21 cidades LATAM de `mercado/config.py` → `index/config.py`
- [ ] INDEX `collect_from_github` para TODAS cidades (já faz algumas)
- [ ] Validar que /startups continua crescendo
- [ ] Testar INDEX isolado com scraping completo

### Fase 3 — MERCADO v2 implementation
- [ ] Reescrever `mercado/collector.py` (funding_rounds query + RSS setorial)
- [ ] Reescrever `mercado/classifier.py` (classificar eventos por setor)
- [ ] Reescrever `mercado/scorer.py` (score de relevância editorial)
- [ ] Reescrever `mercado/synthesizer.py` (estrutura estilo SINTESE)
- [ ] Expandir `mercado/writer.py`: `write_sector_analysis()`, `write_callouts()`
- [ ] Agent.py refatorado com nova lógica
- [ ] Metadata: section_labels + callouts + topics + companies_mentioned (como SINTESE)

### Fase 4 — Deprecar MERCADO v1
- [ ] Remover imports de `collect_from_github` do MERCADO
- [ ] Rodar MERCADO v2 + gerar cover + publicar semana 17

## Estimativa
~4-6h total em sessão dedicada. Fases 1+2 são baixo risco, Fase 3 é reescrita substantiva.

## Decisões pendentes em runtime

1. **Rotação da "Vertical do trimestre" (15%)**: decidir manualmente por run ou algoritmo (sector com mais funding rounds na semana)?
2. **Limiar de "semana fraca"**: quantos events mínimos pra publicar? 5? 10?
3. **Cross-over com FUNDING**: MERCADO v2 vai citar os mesmos rounds que FUNDING já cobre. Tratar como análise complementar (setor-level vs round-level) ou evitar duplicação?

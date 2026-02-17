# Agent Development Patterns

## Structure
Every agent module in `apps/agents/` MUST follow this structure:
```
apps/agents/{name}/
├── __init__.py      # Exports main agent class
├── config.py        # Data sources, parameters, scheduling
├── collector.py     # Data collection from sources
├── pipeline.py      # Processing workflow
├── output.py        # Content formatting (Markdown/HTML)
├── main.py          # CLI entry point
└── tests/
    ├── __init__.py
    ├── test_collector.py
    ├── test_pipeline.py
    └── test_output.py
```

## Rules
- Every agent MUST inherit from `apps.agents.base.base_agent.BaseAgent`
- Every agent output MUST include a confidence score (0-1)
- Every data point MUST have provenance tracking (source URL, timestamp, method)
- Type hints are REQUIRED on all functions
- Minimum 80% test coverage per agent
- Use `httpx` for async HTTP requests (not requests)
- Use `feedparser` for RSS/Atom feeds
- Log with structured JSON (not print statements)

## Confidence Scoring
- 0.0-0.3: Low confidence (single source, unverified)
- 0.3-0.6: Medium confidence (multiple signals, partially verified)
- 0.6-0.8: High confidence (multi-source verified, cross-validated)
- 0.8-1.0: Very high confidence (multi-source, expert-reviewed, peer-validated)

## Output Format
All agent outputs must be publishable Markdown with YAML frontmatter:
```yaml
---
title: "..."
agent: radar
run_id: "..."
generated_at: "2026-02-16T..."
confidence_dq: 0.8
confidence_ac: 0.7
sources: [...]
---
```

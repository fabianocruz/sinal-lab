# Data Pipeline Patterns

## Architecture
- Apache Airflow for orchestration (DAGs)
- dbt for SQL transformations
- PostgreSQL as primary data store
- Redis for caching and inter-agent communication

## Provenance Tracking
EVERY data point ingested into the system MUST have a provenance record:
```python
{
    "source_url": "https://...",
    "collected_at": "2026-02-16T10:00:00Z",
    "extraction_method": "api|scraper|rss|manual",
    "confidence": 0.0-1.0,
    "collector_agent": "radar|funding|..."
}
```

## Data Quality Rules
- Financial data (funding amounts, revenue): requires 2+ independent sources for "verified" status
- Single-source data: tagged "unverified" with visual indicator
- Company data: cross-reference against LinkedIn, GitHub, company website
- Time-sensitive data: must be dated; data older than 90 days marked "potentially stale"
- Currency normalization: all amounts stored in USD with exchange rate and original currency

## Data Quality Scores
- A: Multi-source verified, recent (<30 days), cross-validated
- B: Single-source plausible, recent
- C: Unverified — requires human review before use in published content
- D: Contradictory sources — escalate to editor

## Testing
- Every DAG must have a data quality test
- Test with realistic sample data (not just happy path)
- Validate schema conformance on every ingestion
- Monitor for data drift (sudden changes in volume or distribution)

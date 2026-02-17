# FastAPI Backend Patterns

## Architecture
- All endpoints under `/api/v1/` prefix
- Routers organized by domain (agents, companies, investors, content, etc.)
- Pydantic v2 for all request/response schemas
- SQLAlchemy 2.0 async sessions
- Dependency injection for DB sessions and auth

## File Organization
```
apps/api/
├── main.py              # FastAPI app, CORS, middleware, router includes
├── config.py            # Settings (from env vars via pydantic-settings)
├── deps.py              # Dependency injection (db session, auth)
├── routers/
│   ├── agents.py        # /api/v1/agents/...
│   ├── companies.py     # /api/v1/companies/...
│   ├── investors.py     # /api/v1/investors/...
│   ├── funding.py       # /api/v1/funding/...
│   ├── content.py       # /api/v1/content/...
│   └── ecosystems.py    # /api/v1/ecosystems/...
├── schemas/             # Pydantic request/response models
├── services/            # Business logic layer
└── tests/
    ├── conftest.py      # Fixtures (test db, client)
    └── test_*.py        # Test files per router
```

## Rules
- EVERY endpoint MUST validate input with Pydantic
- EVERY endpoint MUST have proper HTTP status codes
- EVERY list endpoint MUST support pagination (limit/offset)
- Use async/await for all database operations
- Return consistent error format: `{"detail": "message", "code": "ERROR_CODE"}`
- Log all requests with structured JSON
- Rate limiting on public endpoints
- CORS restricted to CORS_ORIGINS env var

## Database Access
- Use repository pattern for data access
- Never raw SQL in routers — always through SQLAlchemy models
- Use `select()` style (SQLAlchemy 2.0), not legacy `query()`

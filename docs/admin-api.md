# Admin Console API Documentation

Complete reference for all admin console API endpoints.

**Base URL:** `http://localhost:8000` (development) | `https://api.sinal.ai` (production)

**Authentication:** None (MVP). **MUST** add authentication before production.

---

## Agent Management

### List Agent Runs

```http
GET /api/agents/runs
```

**Query Parameters:**
- `agent_name` (optional): Filter by agent name (e.g., "sintese", "radar", "codigo")
- `status` (optional): Filter by status (e.g., "completed", "running", "failed")
- `limit` (optional): Number of results (1-100, default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "run_id": "run_abc123",
    "agent_name": "sintese",
    "status": "completed",
    "started_at": "2026-02-16T10:00:00Z",
    "completed_at": "2026-02-16T10:05:30Z",
    "items_processed": 842,
    "avg_confidence": 0.75,
    "error_count": 0,
    "data_sources": {
      "hackernews": { "items": 120, "url": "https://news.ycombinator.com/rss" }
    }
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/agents/runs?agent_name=sintese&limit=10
```

---

### Get Agent Run Detail

```http
GET /api/agents/runs/{run_id}
```

**Path Parameters:**
- `run_id`: Unique run identifier

**Response:** Same as List Agent Runs (single object)

**Example:**
```bash
curl http://localhost:8000/api/agents/runs/run_abc123
```

---

### Get Agent Summary

```http
GET /api/agents/summary
```

Returns latest run summary for each agent.

**Response:**
```json
[
  {
    "agent_name": "sintese",
    "last_run": "2026-02-15T00:00:00Z",
    "status": "completed",
    "items_processed": 842,
    "avg_confidence": 0.7,
    "sources": 37,
    "error_count": 0
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/agents/summary
```

---

### Trigger Agent Run

```http
POST /api/agents/runs/{agent_name}/trigger
```

**Path Parameters:**
- `agent_name`: Agent to trigger ("sintese", "radar", "codigo", "funding", "mercado")

**Response:**
```json
{
  "message": "Agent 'sintese' run triggered",
  "status": "queued",
  "note": "Manual trigger is a placeholder — production will use a task queue"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/agents/runs/sintese/trigger
```

---

## Content Review

### List Review Queue

```http
GET /api/editorial/queue
```

**Query Parameters:**
- `limit` (optional): Number of results (1-100, default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "id": "content_001",
    "title": "Top 10 LATAM Startups to Watch in 2026",
    "slug": "top-10-latam-startups-2026",
    "content_type": "DATA_REPORT",
    "agent_name": "sintese",
    "review_status": "review",
    "confidence_dq": 0.75,
    "confidence_ac": 0.68
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/editorial/queue?limit=50
```

---

### Run Editorial Pipeline

```http
POST /api/editorial/review
```

**Request Body:**
```json
{
  "content_slug": "top-10-latam-startups-2026"
}
```

**Response:**
```json
{
  "content_title": "Top 10 LATAM Startups to Watch in 2026",
  "agent_name": "sintese",
  "run_id": "top-10-latam-startups-2026",
  "publish_ready": true,
  "overall_grade": "A",
  "blocker_count": 0,
  "layers_run": 6,
  "total_flags": 2,
  "byline": "Curated by SINTESE • Verified by editorial pipeline"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/editorial/review \
  -H "Content-Type: application/json" \
  -d '{"content_slug": "top-10-latam-startups-2026"}'
```

---

### Approve Content for Publication

```http
POST /api/editorial/approve/{slug}
```

**Path Parameters:**
- `slug`: Content slug to approve

**Request Body (optional):**
```json
{
  "reviewer_name": "Admin Console",
  "notes": "Looks good"
}
```

**Response:**
```json
{
  "message": "Content 'top-10-latam-startups-2026' approved and published",
  "slug": "top-10-latam-startups-2026",
  "review_status": "published",
  "reviewer": "Admin Console"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/editorial/approve/top-10-latam-startups-2026 \
  -H "Content-Type: application/json" \
  -d '{"reviewer_name": "Admin"}'
```

---

## Content

### List Content

```http
GET /api/content
```

**Query Parameters:**
- `content_type` (optional): Filter by type (e.g., "DATA_REPORT")
- `agent_name` (optional): Filter by agent
- `status` (optional): Filter by review status ("draft", "review", "published")
- `limit` (optional): Number of results (1-100, default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Response:** Same as Review Queue

**Example:**
```bash
curl "http://localhost:8000/api/content?status=published&limit=10"
```

---

### Get Content by Slug

```http
GET /api/content/{slug}
```

**Response:** Full content detail including `body_md`, `body_html`, `sources`, etc.

---

## Companies

### List Companies

```http
GET /api/companies
```

**Query Parameters:**
- `sector` (optional): Filter by sector
- `city` (optional): Filter by city
- `country` (optional): Filter by country
- `status` (optional): Filter by status (default: "active")
- `limit` (optional): Number of results (1-100, default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "id": "company_001",
    "name": "Nubank",
    "slug": "nubank",
    "sector": "Fintech",
    "city": "São Paulo",
    "country": "Brazil",
    "status": "active",
    "website": "https://nubank.com.br"
  }
]
```

**Example:**
```bash
curl "http://localhost:8000/api/companies?country=Brazil&sector=Fintech"
```

---

### Get Company by Slug

```http
GET /api/companies/{slug}
```

**Response:** Single company object

---

## Waitlist

### Get Waitlist Count

```http
GET /api/waitlist/count
```

**Response:**
```json
{
  "count": 127
}
```

---

### List Waitlist Users

```http
GET /api/waitlist/list
```

**Query Parameters:**
- `limit` (optional): Number of results (1-500, default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "id": "user_001",
    "email": "founder@startup.com",
    "name": "João Silva",
    "role": "CTO",
    "company": "TechStartup LTDA",
    "waitlist_position": 1,
    "created_at": "2026-02-10T14:30:00Z"
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/waitlist/list?limit=500
```

**Security Note:** This endpoint exposes PII. MUST add authentication before production.

---

## Error Responses

All endpoints follow a consistent error format:

```json
{
  "detail": "Agent 'unknown' not found",
  "code": "NOT_FOUND"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found
- `409` - Conflict (e.g., duplicate entry)
- `500` - Internal Server Error

---

## Rate Limiting

**MVP:** No rate limiting implemented.

**Production:** Recommended rate limits:
- GET endpoints: 100 requests/minute
- POST endpoints: 10 requests/minute
- Manual trigger: 5 requests/hour

---

## CORS

Configured to accept requests from:
- `http://localhost:3000` (development)
- `https://sinal.ai` (production)
- `https://admin.sinal.ai` (production admin)

---

## Testing

Test all endpoints using the auto-generated API docs:
```
http://localhost:8000/docs
```

Or use the provided fixtures in `apps/web/src/lib/__tests__/fixtures.ts` for integration tests.

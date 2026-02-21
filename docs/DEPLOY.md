# Deploy Guide — Sinal.ai Staging

## Architecture

```
[Vercel] ──── Next.js frontend (apps/web)
    │
    │ rewrites /api/v1/* →
    ▼
[Railway/Render] ──── FastAPI backend (apps/api)
    │
    ├── [Neon] PostgreSQL 16
    └── [Upstash] Redis 7
```

## 1. Frontend (Vercel)

The `vercel.json` is pre-configured for monorepo deployment.

### Setup
1. Connect GitHub repo to Vercel
2. Framework: Next.js (auto-detected)
3. Root directory: leave empty (vercel.json handles it)

### Environment Variables (Vercel Dashboard)
| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://api.sinal.ai` (or Railway/Render URL) |
| `NEXT_PUBLIC_SITE_URL` | `https://sinal.ai` (or Vercel preview URL) |
| `NEXTAUTH_URL` | Same as NEXT_PUBLIC_SITE_URL |
| `NEXTAUTH_SECRET` | Generate with `openssl rand -base64 32` |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |

## 2. Database (Neon or Railway PostgreSQL)

### Option A: Neon (recommended — serverless, free tier)
1. Create project at neon.tech
2. Copy connection string: `postgresql://user:pass@host/dbname?sslmode=require`

### Option B: Railway PostgreSQL
1. Create PostgreSQL service on Railway
2. Copy DATABASE_URL from service variables

### Run Migrations
```bash
DATABASE_URL="postgresql://..." alembic -c packages/database/alembic.ini upgrade head
```
This runs 3 migrations: initial schema, evidence items, auth fields.

## 3. Redis (Upstash)

1. Create database at upstash.com (free tier)
2. Copy Redis URL: `rediss://default:token@host:port`

## 4. API Backend (Railway or Render)

### Option A: Railway (recommended)
1. Create new project → Deploy from GitHub
2. Set root directory: `apps/api`
3. Railway auto-detects Dockerfile

### Option B: Render
1. Create Web Service → Docker
2. Dockerfile path: `apps/api/Dockerfile`
3. Docker context: `.` (root)

### Environment Variables (API)
| Variable | Value |
|----------|-------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Upstash Redis URL |
| `CORS_ORIGINS` | Vercel frontend URL |
| `API_ENV` | `staging` |
| `ANTHROPIC_API_KEY` | For AI agents |
| `RESEND_API_KEY` | For emails and broadcasts |
| `RESEND_FROM_EMAIL` | `news@sinal.tech` |
| `RESEND_AUDIENCE_ID` | Resend Audience for broadcasts |

## 5. Verification Checklist

```bash
# API health
curl https://your-api-url/health

# API endpoints
curl https://your-api-url/api/agents

# Frontend
# Visit Vercel URL — landing page should load
# Visit /newsletter — archive should render
# Visit /login — auth page should load

# Auth flow
# 1. Register at /cadastro
# 2. Login at /login
# 3. Visit /newsletter/[slug] — full content visible
```

## 6. DNS (when ready for production)

| Record | Type | Value |
|--------|------|-------|
| `sinal.ai` | CNAME | `cname.vercel-dns.com` |
| `api.sinal.ai` | CNAME | Railway/Render URL |

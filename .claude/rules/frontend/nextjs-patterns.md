# Next.js Frontend Patterns

## Architecture
- Use App Router exclusively (no Pages Router)
- Server Components by default; Client Components only when interactivity is needed
- Mark client components with `"use client"` at the top of the file

## File Organization
```
apps/web/
├── app/
│   ├── layout.tsx           # Root layout (metadata, fonts, providers)
│   ├── page.tsx             # Landing page
│   ├── globals.css          # Tailwind + global styles
│   ├── (marketing)/         # Marketing pages group
│   ├── (dashboard)/         # Dashboard pages group (future)
│   ├── newsletter/[slug]/   # Newsletter archive
│   ├── agentes/[name]/      # Agent dashboards
│   ├── startup/[slug]/      # Programmatic SEO (future)
│   └── api/                 # API routes (email capture, etc.)
├── components/
│   ├── ui/                  # shadcn/ui components
│   └── ...                  # Feature components
├── lib/                     # Utilities, API client, constants
└── public/                  # Static assets
```

## Rules
- All pages MUST have metadata (title, description, OG tags)
- All dynamic pages MUST use SSR (not SSG) for data freshness
- Loading states (`loading.tsx`) required for all data-fetching pages
- Error boundaries (`error.tsx`) required for all pages
- Mobile-first: design for 375px width, then scale up
- Images: use `next/image` with explicit width/height
- Links: use `next/link` for all internal navigation
- JSON-LD structured data on every public page

## SEO
- Every page needs: title, meta description, canonical URL, OG image
- Programmatic pages: min 300 unique words, JSON-LD, internal links
- Sitemaps: segmented by content type
- hreflang: pt-BR (future: es)

## Performance
- Target Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1
- Use dynamic imports for heavy client components
- Minimize client-side JavaScript bundle

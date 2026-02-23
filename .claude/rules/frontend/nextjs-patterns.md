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
│   ├── newsletter/[slug]/   # Newsletter detail page
│   ├── startups/            # Startup listing page (SSR + ISR)
│   ├── startup/[slug]/      # Startup detail + JSON-LD (SSR + ISR)
│   ├── agentes/[name]/      # Agent dashboards
│   └── api/                 # API routes (email capture, etc.)
├── components/
│   ├── ui/                  # shadcn/ui components
│   ├── newsletter/          # Newsletter components (ArchiveCard, Pagination, SearchBar, etc.)
│   ├── startup/             # Startup components (CompanyCard, CompanyDetail, SectorFilter)
│   └── ...                  # Feature components
├── lib/                     # Utilities, API client, types, constants
│   ├── api.ts               # API client (fetchNewsletters, fetchCompanies, etc.)
│   ├── company.ts           # Company type + SECTOR_OPTIONS
│   ├── newsletter.ts        # Newsletter types + FALLBACK_NEWSLETTERS
│   └── jsonld.ts            # JSON-LD helpers (companyJsonLd)
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

## Reusable Components
- `Pagination` and `SearchBar` accept `basePath` prop (defaults to `/newsletter`)
- When adding new listing pages, pass `basePath="/your-path"` to reuse these components
- `SectorFilter` is a Client Component using `useSearchParams`/`useRouter` for URL-based filtering
- New listing pages should follow `/startups` pattern: SSR Server Component, `searchParams`, filter + grid + pagination

## SEO
- Every page needs: title, meta description, canonical URL, OG image
- Programmatic pages: min 300 unique words, JSON-LD, internal links
- JSON-LD helpers live in `lib/jsonld.ts` — use `companyJsonLd()` as reference for new entity types
- Sitemap (`app/sitemap.ts`) is async — fetches dynamic slugs from API with try/catch fallback
- Sitemaps: segmented by content type
- hreflang: pt-BR (future: es)

## Performance
- Target Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1
- Use dynamic imports for heavy client components
- Minimize client-side JavaScript bundle

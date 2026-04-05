// Feed skeleton shown while the Server Component is fetching data.

function FeedItemSkeleton() {
  return (
    <div className="border-b border-[rgba(255,255,255,0.05)] py-6">
      {/* Header row */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-5 w-20 animate-pulse rounded bg-sinal-graphite" />
          <div className="h-4 w-12 animate-pulse rounded bg-sinal-graphite" />
        </div>
        <div className="h-3 w-8 animate-pulse rounded bg-sinal-graphite" />
      </div>
      {/* Author */}
      <div className="mb-3 flex items-center gap-2.5">
        <div className="h-9 w-9 animate-pulse rounded-full bg-sinal-graphite" />
        <div className="h-4 w-36 animate-pulse rounded bg-sinal-graphite" />
      </div>
      {/* Text lines */}
      <div className="mb-4 space-y-2">
        <div className="h-4 w-full animate-pulse rounded bg-sinal-graphite" />
        <div className="h-4 w-full animate-pulse rounded bg-sinal-graphite" />
        <div className="h-4 w-3/4 animate-pulse rounded bg-sinal-graphite" />
      </div>
      {/* Metrics */}
      <div className="flex items-center gap-4">
        <div className="h-3 w-12 animate-pulse rounded bg-sinal-graphite" />
        <div className="h-3 w-12 animate-pulse rounded bg-sinal-graphite" />
        <div className="ml-auto h-3 w-20 animate-pulse rounded bg-sinal-graphite" />
      </div>
    </div>
  );
}

function SidebarItemSkeleton() {
  return (
    <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-4">
      <div className="mb-2 h-3 w-24 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
      <div className="mb-2 h-4 w-full animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
      <div className="h-[3px] w-full animate-pulse rounded-full bg-[rgba(255,255,255,0.06)]" />
    </div>
  );
}

export default function FeedLoading() {
  return (
    <div className="pt-[72px]">
      <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)]">
        {/* Header skeleton */}
        <div className="py-10">
          <div className="mb-2 h-8 w-48 animate-pulse rounded-lg bg-sinal-graphite" />
          <div className="h-4 w-96 animate-pulse rounded bg-sinal-graphite" />
        </div>

        {/* Filter bar skeleton */}
        <div className="mb-8 space-y-3">
          <div className="flex gap-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-8 w-20 animate-pulse rounded-lg bg-sinal-graphite" />
            ))}
          </div>
          <div className="flex gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-8 w-24 animate-pulse rounded-lg bg-sinal-graphite" />
            ))}
          </div>
        </div>

        {/* Main layout */}
        <div className="flex gap-8">
          {/* Feed column */}
          <div className="min-w-0 flex-1">
            {Array.from({ length: 6 }).map((_, i) => (
              <FeedItemSkeleton key={i} />
            ))}
          </div>

          {/* Sidebar column */}
          <aside className="hidden w-[280px] shrink-0 space-y-3 lg:block">
            <div className="mb-4 h-3 w-20 animate-pulse rounded bg-sinal-graphite" />
            {Array.from({ length: 5 }).map((_, i) => (
              <SidebarItemSkeleton key={i} />
            ))}
          </aside>
        </div>
      </div>
    </div>
  );
}

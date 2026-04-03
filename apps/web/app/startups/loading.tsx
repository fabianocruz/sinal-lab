function CompanyCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-sinal-slate bg-sinal-graphite">
      {/* Accent bar */}
      <div className="h-[2px] bg-[rgba(255,255,255,0.04)]" />

      <div className="flex flex-col px-5 pb-4 pt-5">
        {/* Header: logo + name + location */}
        <div className="mb-3 flex items-start gap-3">
          <div className="h-10 w-10 shrink-0 animate-pulse rounded-[10px] bg-[rgba(255,255,255,0.06)]" />
          <div className="flex-1">
            <div className="mb-1.5 h-4 w-3/4 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          </div>
        </div>

        {/* Description */}
        <div className="mb-3.5 space-y-1.5">
          <div className="h-3 w-full animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          <div className="h-3 w-5/6 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
        </div>

        {/* Tags */}
        <div className="mb-4 flex gap-1.5">
          <div className="h-5 w-14 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          <div className="h-5 w-16 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          <div className="h-5 w-12 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
        </div>

        {/* Stats bar */}
        <div className="mt-auto flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] pt-3">
          <div>
            <div className="mb-1 h-4 w-12 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
            <div className="h-2.5 w-8 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          </div>
          <div>
            <div className="mb-1 h-4 w-16 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
            <div className="h-2.5 w-10 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          </div>
          <div>
            <div className="mb-1 h-4 w-8 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
            <div className="h-2.5 w-10 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function StartupsLoading() {
  return (
    <div className="pt-[72px]">
      <div className="mx-auto max-w-[1120px] px-[clamp(20px,4vw,48px)] py-10">
        {/* Header skeleton */}
        <div className="mb-10 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="h-10 w-64 animate-pulse rounded-lg bg-sinal-graphite" />
            <div className="mt-2 h-4 w-80 animate-pulse rounded bg-sinal-graphite" />
          </div>
          <div className="h-12 w-[280px] animate-pulse rounded-[10px] bg-sinal-graphite" />
        </div>

        {/* Filter pills skeleton */}
        <div className="mb-8 flex gap-2 overflow-hidden">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-9 w-20 shrink-0 animate-pulse rounded-lg bg-sinal-graphite" />
          ))}
        </div>

        {/* Cards skeleton */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <CompanyCardSkeleton key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}

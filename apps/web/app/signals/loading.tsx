function ClusterCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-sinal-slate bg-sinal-graphite">
      {/* Accent bar */}
      <div className="h-[2px] bg-[rgba(255,255,255,0.04)]" />

      <div className="flex flex-col px-5 pb-4 pt-5">
        {/* Header */}
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="mb-1.5 h-4 w-3/4 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          </div>
          <div className="h-5 w-20 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
        </div>

        {/* Description */}
        <div className="mb-4 space-y-1.5">
          <div className="h-3 w-full animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          <div className="h-3 w-5/6 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
        </div>

        {/* Score bar */}
        <div className="mb-4 h-[3px] w-full animate-pulse rounded-full bg-[rgba(255,255,255,0.06)]" />

        {/* Bottom stats */}
        <div className="mt-auto flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] pt-3">
          <div>
            <div className="mb-1 h-4 w-10 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
            <div className="h-2.5 w-8 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          </div>
          <div>
            <div className="mb-1 h-4 w-8 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
            <div className="h-2.5 w-8 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          </div>
          <div className="flex gap-1">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-2 w-2 animate-pulse rounded-full bg-[rgba(255,255,255,0.06)]"
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SignalCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-sinal-slate bg-sinal-graphite">
      <div className="h-[2px] bg-[rgba(255,255,255,0.04)]" />
      <div className="px-4 pb-4 pt-4">
        {/* Header */}
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 animate-pulse rounded-full bg-[rgba(255,255,255,0.06)]" />
            <div>
              <div className="mb-1 h-3.5 w-24 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
              <div className="h-3 w-16 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
            </div>
          </div>
          <div className="h-5 w-16 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
        </div>

        {/* Text */}
        <div className="mb-3 space-y-1.5">
          <div className="h-3 w-full animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          <div className="h-3 w-full animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          <div className="h-3 w-2/3 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] pt-3">
          <div className="flex gap-3">
            <div className="h-3 w-12 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
            <div className="h-3 w-14 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
          </div>
          <div className="h-3 w-14 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
        </div>
      </div>
    </div>
  );
}

export default function SignalsLoading() {
  return (
    <div className="pt-[72px]">
      <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)] py-12">
        {/* Header skeleton */}
        <div className="mb-10 flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="mb-2 h-3 w-20 animate-pulse rounded bg-sinal-graphite" />
            <div className="mb-2 h-9 w-72 animate-pulse rounded-lg bg-sinal-graphite" />
            <div className="h-4 w-80 animate-pulse rounded bg-sinal-graphite" />
          </div>
          <div className="h-16 w-[360px] animate-pulse rounded-xl bg-sinal-graphite" />
        </div>

        {/* Clusters header */}
        <div className="mb-6">
          <div className="mb-1 h-6 w-44 animate-pulse rounded bg-sinal-graphite" />
          <div className="h-3.5 w-64 animate-pulse rounded bg-sinal-graphite" />
        </div>

        {/* Cluster grid skeleton */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <ClusterCardSkeleton key={i} />
          ))}
        </div>

        {/* Signal feed header */}
        <div className="mt-12 mb-6">
          <div className="mb-1 h-6 w-40 animate-pulse rounded bg-sinal-graphite" />
          <div className="h-3.5 w-56 animate-pulse rounded bg-sinal-graphite" />
        </div>

        {/* Platform filter pills skeleton */}
        <div className="mb-6 flex gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-9 w-20 animate-pulse rounded-lg bg-sinal-graphite" />
          ))}
        </div>

        {/* Signal grid skeleton */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SignalCardSkeleton key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}

function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="overflow-hidden rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
      <div className="mb-3 h-4 w-1/3 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="h-3 animate-pulse rounded bg-[rgba(255,255,255,0.04)]"
            style={{ width: i === lines - 1 ? "70%" : "100%" }}
          />
        ))}
      </div>
    </div>
  );
}

function TabsSkeleton() {
  return (
    <div className="flex gap-1 border-b border-sinal-slate">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-10 w-28 animate-pulse rounded-t-lg bg-sinal-graphite" />
      ))}
    </div>
  );
}

function PulsePanelSkeleton() {
  return (
    <div className="space-y-6">
      {/* Two-column */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <CardSkeleton lines={5} />
        <CardSkeleton lines={5} />
      </div>

      {/* Narratives */}
      <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
        <div className="mb-4 h-3 w-32 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
        <div className="flex flex-wrap gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-9 w-36 animate-pulse rounded-lg bg-[rgba(255,255,255,0.04)]"
            />
          ))}
        </div>
      </div>

      {/* Heatmap */}
      <div className="rounded-xl border border-sinal-slate bg-sinal-graphite p-5">
        <div className="mb-4 h-3 w-40 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex gap-2">
              <div className="h-6 w-32 animate-pulse rounded bg-[rgba(255,255,255,0.04)]" />
              {Array.from({ length: 4 }).map((_, j) => (
                <div
                  key={j}
                  className="h-6 w-6 animate-pulse rounded bg-[rgba(255,255,255,0.04)]"
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function SignalsLoading() {
  return (
    <div className="pt-[72px]">
      <div className="mx-auto max-w-[1280px] px-[clamp(20px,4vw,32px)]">
        {/* Header skeleton */}
        <div className="flex flex-wrap items-end justify-between gap-6 py-12">
          <div>
            <div className="mb-2 h-3 w-20 animate-pulse rounded bg-sinal-graphite" />
            <div className="mb-2 h-9 w-72 animate-pulse rounded-lg bg-sinal-graphite" />
            <div className="h-4 w-80 animate-pulse rounded bg-sinal-graphite" />
          </div>
          <div className="h-16 w-[360px] animate-pulse rounded-xl bg-sinal-graphite" />
        </div>

        {/* Tabs skeleton */}
        <TabsSkeleton />

        {/* Panel skeleton */}
        <div className="py-8">
          <PulsePanelSkeleton />
        </div>
      </div>
    </div>
  );
}

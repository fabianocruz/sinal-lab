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
        <div className="mb-8 flex gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-9 w-20 animate-pulse rounded-lg bg-sinal-graphite" />
          ))}
        </div>

        {/* Cards skeleton */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="h-[200px] animate-pulse rounded-2xl bg-sinal-graphite" />
          ))}
        </div>
      </div>
    </div>
  );
}

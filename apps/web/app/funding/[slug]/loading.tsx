export default function FundingSlugLoading() {
  return (
    <div className="pt-[72px]">
      <article className="mx-auto max-w-[720px] px-6 py-12 md:px-10">
        {/* Back link skeleton */}
        <div className="mb-8 h-4 w-32 animate-pulse rounded bg-sinal-graphite" />

        {/* Header skeleton */}
        <header className="mb-10 border-b border-[rgba(255,255,255,0.06)] pb-10">
          <div className="mb-4 flex gap-3">
            <div className="h-4 w-20 animate-pulse rounded bg-sinal-graphite" />
            <div className="h-4 w-32 animate-pulse rounded bg-sinal-graphite" />
          </div>
          <div className="mb-3 h-10 w-full animate-pulse rounded-lg bg-sinal-graphite" />
          <div className="mb-1 h-10 w-3/4 animate-pulse rounded-lg bg-sinal-graphite" />
          <div className="mt-4 h-5 w-2/3 animate-pulse rounded bg-sinal-graphite" />
          <div className="mt-6 flex items-center gap-3">
            <div className="h-8 w-8 animate-pulse rounded-full bg-sinal-graphite" />
            <div>
              <div className="mb-1 h-4 w-28 animate-pulse rounded bg-sinal-graphite" />
              <div className="h-3 w-20 animate-pulse rounded bg-sinal-graphite" />
            </div>
          </div>
        </header>

        {/* Body skeleton */}
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-5 animate-pulse rounded bg-sinal-graphite"
              style={{ width: `${85 + (i % 3) * 5}%` }}
            />
          ))}
        </div>
      </article>
    </div>
  );
}

export default function StartupDetailLoading() {
  return (
    <div className="pt-[72px]">
      <div className="mx-auto max-w-[720px] px-6 py-12 md:px-10">
        <div className="mb-8 h-4 w-32 animate-pulse rounded bg-sinal-graphite" />
        <div className="mb-10 border-b border-[rgba(255,255,255,0.06)] pb-10">
          <div className="mb-4 h-6 w-24 animate-pulse rounded bg-sinal-graphite" />
          <div className="mb-4 h-10 w-3/4 animate-pulse rounded-lg bg-sinal-graphite" />
          <div className="h-4 w-48 animate-pulse rounded bg-sinal-graphite" />
          <div className="mt-4 h-20 animate-pulse rounded-lg bg-sinal-graphite" />
        </div>
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-sinal-graphite" />
          ))}
        </div>
      </div>
    </div>
  );
}

import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

export default function IntelligenceLoading() {
  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <div className="mx-auto max-w-[1120px] px-[clamp(20px,4vw,48px)] py-10">
          <div className="mb-10">
            <div className="h-10 w-48 animate-pulse rounded bg-sinal-graphite" />
            <div className="mt-2 h-5 w-80 animate-pulse rounded bg-sinal-graphite" />
          </div>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="overflow-hidden rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite"
              >
                <div className="aspect-[16/10] animate-pulse bg-[rgba(255,255,255,0.03)]" />
                <div className="space-y-3 px-[22px] pb-6 pt-5">
                  <div className="h-3 w-20 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
                  <div className="h-5 w-full animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
                  <div className="h-4 w-3/4 animate-pulse rounded bg-[rgba(255,255,255,0.06)]" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

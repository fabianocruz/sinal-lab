import type { SignalStats } from "@/lib/signal";

interface StatsBarProps {
  stats: SignalStats;
}

function StatBox({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="flex flex-col items-center text-center sm:items-start sm:text-left">
      <div className="font-display text-[28px] leading-none text-signal">{value}</div>
      <div className="mt-1 font-mono text-[9px] uppercase tracking-[1px] text-[#4A4A56]">
        {label}
      </div>
    </div>
  );
}

function Divider() {
  return <div className="hidden h-8 w-px bg-sinal-slate sm:block" aria-hidden="true" />;
}

export default function StatsBar({ stats }: StatsBarProps) {
  const platformCount = Object.keys(stats.platforms).length;
  const themeCount = Object.keys(stats.themes).length;

  return (
    <div className="flex flex-wrap items-center justify-center gap-6 rounded-xl border border-sinal-slate bg-sinal-graphite px-6 py-4 sm:justify-start">
      <StatBox value={stats.total_signals.toLocaleString("pt-BR")} label="Sinais" />
      <Divider />
      <StatBox value={stats.total_clusters} label="Clusters" />
      <Divider />
      <StatBox value={platformCount || "—"} label="Plataformas" />
      <Divider />
      <StatBox value={themeCount || "—"} label="Temas" />
    </div>
  );
}

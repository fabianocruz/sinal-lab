// No Recharts needed — pure CSS/Tailwind progress bar
// This is a Server Component (no "use client" directive needed)

interface ScoreBarProps {
  score: number; // 0 to 1
  label?: string;
  color?: string;
}

export default function ScoreBar({ score, label, color = "#E8FF59" }: ScoreBarProps) {
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);

  return (
    <div className="w-full">
      <div className="mb-1.5 flex items-center justify-between">
        {label && <span className="font-mono text-[12px] text-silver">{label}</span>}
        <span className="font-mono text-[12px] tabular-nums" style={{ color }}>
          {pct}%
        </span>
      </div>
      <div
        className="h-[3px] w-full overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? "Score"}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

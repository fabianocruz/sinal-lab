interface ReadingTimeProps {
  /** Estimated reading time in minutes. Undefined/0 = no render. */
  minutes: number | undefined;
}

/** Monospace reading time indicator (e.g. "5 min de leitura"). Returns null when minutes is falsy. */
export default function ReadingTime({ minutes }: ReadingTimeProps) {
  if (!minutes || minutes < 1) return null;

  return (
    <span className="font-mono text-[11px] tracking-[0.5px] text-ash">
      {minutes} min de leitura
    </span>
  );
}

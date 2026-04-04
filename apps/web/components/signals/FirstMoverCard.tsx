// Server Component — no interactivity needed.

interface FirstMover {
  handle: string;
  name?: string;
  posted_at?: string; // ISO string
}

interface FirstMoverCardProps {
  firstMover: FirstMover;
  clusterName: string;
}

function formatRelativeTime(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const hours = Math.floor(diff / 3_600_000);
    const days = Math.floor(diff / 86_400_000);
    if (days > 0) return `ha ${days} dia${days > 1 ? "s" : ""}`;
    if (hours > 0) return `ha ${hours}h`;
    return "recentemente";
  } catch {
    return "";
  }
}

export default function FirstMoverCard({ firstMover, clusterName }: FirstMoverCardProps) {
  const displayName = firstMover.name || `@${firstMover.handle}`;
  const timeLabel = firstMover.posted_at ? formatRelativeTime(firstMover.posted_at) : null;

  return (
    <div className="mt-3 flex items-center gap-2.5 rounded-lg border border-[rgba(89,255,180,0.12)] bg-[rgba(89,255,180,0.04)] px-3 py-2">
      {/* Avatar placeholder */}
      <div
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[rgba(89,255,180,0.15)] font-mono text-[10px] font-semibold text-[#59FFB4]"
        aria-hidden="true"
      >
        {displayName.charAt(0).toUpperCase()}
      </div>

      <p className="min-w-0 text-[11px] leading-[1.4] text-ash">
        <span className="font-semibold text-[#59FFB4]">{displayName}</span>
        {" foi o primeiro a falar sobre "}
        <span className="text-silver">{clusterName}</span>
        {timeLabel && (
          <span className="ml-1 font-mono text-[10px] text-[#4A4A56]">{timeLabel}</span>
        )}
      </p>
    </div>
  );
}

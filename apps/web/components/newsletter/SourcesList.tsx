"use client";

import { ExternalLink } from "lucide-react";

interface SourcesListProps {
  sources: string[];
  agentColor?: string;
}

function extractHostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function deduplicateByHostname(sources: string[]): string[] {
  const seen = new Set<string>();
  return sources.filter((url) => {
    const hostname = extractHostname(url);
    if (seen.has(hostname)) return false;
    seen.add(hostname);
    return true;
  });
}

export default function SourcesList({ sources, agentColor = "#E8FF59" }: SourcesListProps) {
  if (sources.length === 0) return null;

  const unique = deduplicateByHostname(sources);

  return (
    <section id="fontes" className="mt-10 border-t border-[rgba(255,255,255,0.06)] pt-8">
      <h3 className="mb-4 font-mono text-[11px] uppercase tracking-[1.5px] text-ash">Fontes</h3>
      <div className="flex flex-wrap gap-2">
        {unique.map((url) => (
          <a
            key={url}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-3 py-1.5 font-mono text-[12px] text-silver transition-colors hover:border-[rgba(255,255,255,0.12)] hover:text-bone"
          >
            <span
              className="inline-block h-[4px] w-[4px] shrink-0 rounded-full"
              style={{ backgroundColor: agentColor }}
              aria-hidden="true"
            />
            {extractHostname(url)}
            <ExternalLink className="h-3 w-3 text-ash" />
          </a>
        ))}
      </div>
    </section>
  );
}

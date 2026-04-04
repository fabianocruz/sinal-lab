"use client";

import { useState } from "react";
import type { Signal } from "@/lib/signal";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ISO week number (1-53) from a Date
function isoWeek(date: Date): number {
  const tmp = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  // Thursday in current week decides the year
  tmp.setUTCDate(tmp.getUTCDate() + 4 - (tmp.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
  return Math.ceil(((tmp.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

function signalsToCsv(signals: Signal[]): string {
  const headers = [
    "platform",
    "author",
    "text",
    "theme",
    "sentiment",
    "published_at",
    "url",
    "likes",
    "replies",
  ];

  const rows = signals.map((s) => {
    const author = s.author_display_name || s.author_handle;
    const text = `"${(s.text || "").replace(/"/g, '""').slice(0, 200)}"`;
    return [
      s.platform,
      author,
      text,
      s.theme,
      s.sentiment?.toFixed(2) ?? "0",
      s.published_at || "",
      s.post_url,
      s.metrics?.likes ?? 0,
      s.metrics?.replies ?? 0,
    ].join(",");
  });

  return [headers.join(","), ...rows].join("\n");
}

function triggerDownload(csv: string, filename: string) {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default function ExportButton() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExport() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/signals?limit=500`);

      if (!response.ok) {
        throw new Error(`Erro ao buscar sinais (${response.status})`);
      }

      const data: { items: Signal[]; total: number } = await response.json();
      const signals = data.items ?? [];

      if (signals.length === 0) {
        setError("Nenhum sinal disponivel para exportar.");
        return;
      }

      const csv = signalsToCsv(signals);
      const week = isoWeek(new Date());
      const filename = `sinal-signals-week-${week}.csv`;
      triggerDownload(csv, filename);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro desconhecido";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={handleExport}
        disabled={loading}
        aria-label="Exportar sinais como CSV"
        className={[
          "flex items-center gap-2 rounded-lg border px-3 py-2 font-mono text-[11px] uppercase tracking-[0.8px] transition-all duration-200",
          loading
            ? "cursor-not-allowed border-[rgba(255,255,255,0.06)] text-[#4A4A56]"
            : "border-[rgba(255,255,255,0.10)] text-ash hover:border-signal hover:text-signal",
        ].join(" ")}
      >
        {/* Download icon */}
        {loading ? (
          <svg
            className="h-3.5 w-3.5 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        ) : (
          <svg
            className="h-3.5 w-3.5"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
        )}
        {loading ? "Exportando..." : "Export BI"}
      </button>

      {error && (
        <p className="font-mono text-[10px] text-red-400" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

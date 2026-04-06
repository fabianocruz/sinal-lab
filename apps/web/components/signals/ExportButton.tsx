"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ExportButtonProps {
  /** Which export endpoint to call: "signals" or "feed" */
  type?: "signals" | "feed";
  /** Optional theme/category filter passed as query param */
  theme?: string;
}

/**
 * Triggers a server-side CSV export via the /api/export/* endpoints.
 * The API returns a StreamingResponse with Content-Disposition attachment,
 * so we fetch the blob and create a download link.
 */
export default function ExportButton({ type = "signals", theme }: ExportButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExport() {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ format: "csv", limit: "500" });
      if (theme) {
        params.set("theme", theme);
      }

      const response = await fetch(`${API_BASE}/api/export/${type}?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`Erro ao exportar (${response.status})`);
      }

      // Extract filename from Content-Disposition or fall back to default
      const disposition = response.headers.get("content-disposition") || "";
      const filenameMatch = disposition.match(/filename="(.+?)"/);
      const filename = filenameMatch?.[1] || `sinal-${type}-export.csv`;

      const blob = await response.blob();

      if (blob.size === 0) {
        setError("Nenhum dado disponivel para exportar.");
        return;
      }

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
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

"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { usePathname } from "next/navigation";
import MarkdownRenderer from "@/components/newsletter/MarkdownRenderer";

interface IntelligenceGateProps {
  content: string;
  accentColor?: string;
  /** Approximate word count to show as preview for unauthenticated users. */
  previewWords?: number;
}

/** Truncate markdown to approximately `wordLimit` words, preserving word boundaries. */
function truncateToWords(text: string, wordLimit: number): string {
  const words = text.split(/\s+/);
  if (words.length <= wordLimit) return text;
  return words.slice(0, wordLimit).join(" ");
}

/**
 * Shows full content to authenticated users.
 * Shows a ~300-word preview with a blurred overlay and sign-up prompt for
 * unauthenticated or loading states.
 */
export default function IntelligenceGate({
  content,
  accentColor = "#59B4FF",
  previewWords = 300,
}: IntelligenceGateProps) {
  const { status } = useSession();
  const pathname = usePathname();
  const callbackParam = pathname ? `?callbackUrl=${encodeURIComponent(pathname)}` : "";

  if (status === "authenticated") {
    return (
      <div className="prose-sinal">
        <MarkdownRenderer content={content} agentColor={accentColor} />
      </div>
    );
  }

  const preview = truncateToWords(content, previewWords);

  return (
    <div data-testid="intelligence-gate">
      {/* Preview: visible portion */}
      <div className="prose-sinal">
        <MarkdownRenderer content={preview} agentColor={accentColor} />
      </div>

      {/* Blurred continuation hint + gate */}
      <div className="relative mt-[-80px]">
        {/* Gradient fade over bottom of preview */}
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-24"
          style={{
            background:
              "linear-gradient(to bottom, transparent, var(--color-sinal-black, #0A0A0B))",
          }}
          aria-hidden="true"
        />

        {/* Gate card */}
        <div className="relative z-10 mt-12 rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-8 py-10 text-center">
          <div
            className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full"
            style={{ backgroundColor: `${accentColor}15` }}
            aria-hidden="true"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect
                x="4"
                y="9"
                width="12"
                height="9"
                rx="2"
                stroke={accentColor}
                strokeWidth="1.5"
              />
              <path
                d="M7 9V6a3 3 0 116 0v3"
                stroke={accentColor}
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </div>

          <h3 className="mb-2 font-display text-[18px] text-sinal-white">
            Continue lendo gratuitamente
          </h3>
          <p className="mx-auto mb-6 max-w-[380px] text-[14px] leading-relaxed text-ash">
            Crie sua conta gratuita para acessar o relatorio completo, incluindo dados exclusivos e
            analise detalhada.
          </p>

          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Link
              href={`/cadastro${callbackParam}`}
              className="rounded-lg px-6 py-3 font-mono text-[13px] font-semibold text-sinal-black transition-opacity hover:opacity-90"
              style={{ backgroundColor: accentColor }}
            >
              Criar conta gratuita
            </Link>
            <Link
              href={`/login${callbackParam}`}
              className="rounded-lg border border-[rgba(255,255,255,0.08)] px-6 py-3 font-mono text-[13px] text-sinal-white transition-colors hover:bg-[rgba(255,255,255,0.04)]"
            >
              Ja tenho conta
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

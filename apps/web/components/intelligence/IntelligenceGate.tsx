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

/** Truncate markdown to approximately `wordLimit` words, preserving newlines
 * and markdown structure. We count words across the whole string but slice
 * on the original text so paragraph breaks, headings and lists stay intact.
 */
function truncateToWords(text: string, wordLimit: number): string {
  // Walk the original string, counting words (sequences of non-whitespace).
  // Slice when the count reaches the limit so that newlines and other
  // whitespace are preserved exactly as in the source.
  let count = 0;
  let inWord = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const isWs = /\s/.test(ch);
    if (!isWs && !inWord) {
      inWord = true;
      count++;
      if (count > wordLimit) {
        // Back off to the end of the previous word.
        return text.slice(0, i).trimEnd();
      }
    } else if (isWs) {
      inWord = false;
    }
  }
  return text;
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
  const isDev = process.env.NODE_ENV === "development";

  if (isDev || status === "authenticated") {
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
          {/* Social proof badge */}
          <div
            className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border px-3 py-1"
            style={{
              borderColor: `${accentColor}33`,
              backgroundColor: `${accentColor}0F`,
            }}
          >
            <span
              className="block h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: accentColor }}
              aria-hidden="true"
            />
            <span
              className="font-mono text-[11px] font-semibold uppercase tracking-[1px]"
              style={{ color: accentColor }}
            >
              +2.500 fundadores, CTOs e investidores já leem
            </span>
          </div>

          <h3 className="mb-3 font-display text-[22px] leading-tight text-sinal-white">
            O resto do relatório, mais análise semanal de LATAM no seu email.
          </h3>
          <p className="mx-auto mb-6 max-w-[460px] text-[14px] leading-relaxed text-ash">
            Toda semana, 5 relatórios gerados por AI agents com cobertura de funding rounds, market
            maps e sinais técnicos. Grátis. Uma edição por semana. Cancela em 1 clique.
          </p>

          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Link
              href={`/cadastro${callbackParam}`}
              className="rounded-lg px-6 py-3 font-mono text-[13px] font-semibold text-sinal-black transition-opacity hover:opacity-90"
              style={{ backgroundColor: accentColor }}
            >
              Quero o Sinal Semanal →
            </Link>
            <Link
              href={`/login${callbackParam}`}
              className="rounded-lg border border-[rgba(255,255,255,0.08)] px-6 py-3 font-mono text-[13px] text-sinal-white transition-colors hover:bg-[rgba(255,255,255,0.04)]"
            >
              Já tenho conta
            </Link>
          </div>

          <p className="mt-5 font-mono text-[11px] text-ash">
            Plata $405M · Cursor $50B · Ualá $195M · Creditas $108M &nbsp;—&nbsp; tudo coberto na
            edição #55
          </p>
        </div>
      </div>
    </div>
  );
}

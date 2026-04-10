"use client";

import { useState, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FeedbackWidgetProps {
  initialScore?: number;
  source?: string;
  edition?: number;
  contentSlug?: string;
}

export default function FeedbackWidget({
  initialScore,
  source = "newsletter",
  edition,
  contentSlug,
}: FeedbackWidgetProps) {
  const [score, setScore] = useState<number | undefined>(initialScore);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Auto-submit if score came from email link
  useEffect(() => {
    if (initialScore !== undefined && !submitted) {
      handleSubmit(initialScore);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(npsScore?: number) {
    const finalScore = npsScore ?? score;
    if (finalScore === undefined) return;

    setSubmitting(true);
    try {
      await fetch(`${API_BASE}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nps_score: finalScore,
          comment: comment || null,
          source,
          edition,
          content_slug: contentSlug,
        }),
      });
      setSubmitted(true);
    } catch {
      // Silent fail — feedback is best-effort
      setSubmitted(true);
    }
    setSubmitting(false);
  }

  if (submitted) {
    return (
      <div className="text-center">
        <div className="mb-6 flex items-center justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[rgba(89,255,180,0.1)]">
            <svg
              className="h-8 w-8 text-signal"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
        <h1 className="mb-2 font-display text-[28px] text-sinal-white">Obrigado!</h1>
        <p className="mb-6 text-[15px] text-ash">
          Seu feedback sera usado para melhorar a proxima edicao automaticamente.
        </p>
        {score !== undefined && (
          <div className="mb-8 inline-flex items-center gap-2 rounded-lg border border-sinal-slate bg-sinal-graphite px-4 py-2">
            <span className="font-mono text-[13px] text-ash">Sua nota:</span>
            <span className="font-mono text-[18px] font-bold text-signal">{score}</span>
            <span className="font-mono text-[11px] text-[#4A4A56]">/ 10</span>
          </div>
        )}
        {!comment && (
          <div>
            <p className="mb-3 text-[13px] text-ash">Quer deixar um comentario?</p>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="O que podemos melhorar?"
              className="mb-3 w-full rounded-lg border border-sinal-slate bg-sinal-graphite px-4 py-3 font-mono text-[13px] text-sinal-white placeholder-[#4A4A56] outline-none focus:border-signal"
              rows={3}
            />
            <button
              onClick={() => handleSubmit(score)}
              className="rounded-lg bg-signal px-6 py-2.5 font-mono text-[13px] font-bold text-sinal-black transition-all hover:brightness-110"
            >
              Enviar comentario
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="text-center">
      <h1 className="mb-2 font-display text-[28px] text-sinal-white">Como foi esta edicao?</h1>
      <p className="mb-8 text-[15px] text-ash">
        Seu feedback melhora a proxima edicao automaticamente.
      </p>

      {/* NPS buttons */}
      <div className="mb-4 flex justify-center gap-2">
        {Array.from({ length: 11 }, (_, i) => {
          const color = i <= 6 ? "#FF5E5E" : i <= 8 ? "#FFB859" : "#59FFB4";
          const isSelected = score === i;
          return (
            <button
              key={i}
              onClick={() => setScore(i)}
              className="flex h-10 w-10 items-center justify-center rounded-lg font-mono text-[14px] font-semibold transition-all"
              style={{
                backgroundColor: isSelected ? color : "rgba(255,255,255,0.04)",
                color: isSelected ? "#0A0A0B" : color,
                border: `1px solid ${color}${isSelected ? "" : "40"}`,
              }}
            >
              {i}
            </button>
          );
        })}
      </div>
      <div className="mb-8 flex justify-between px-1">
        <span className="font-mono text-[10px] text-[#4A4A56]">Nada util</span>
        <span className="font-mono text-[10px] text-[#4A4A56]">Essencial</span>
      </div>

      {/* Comment */}
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="O que podemos melhorar? (opcional)"
        className="mb-4 w-full rounded-lg border border-sinal-slate bg-sinal-graphite px-4 py-3 font-mono text-[13px] text-sinal-white placeholder-[#4A4A56] outline-none focus:border-signal"
        rows={3}
      />

      <button
        onClick={() => handleSubmit()}
        disabled={score === undefined || submitting}
        className="w-full rounded-lg bg-signal px-6 py-3 font-mono text-[14px] font-bold text-sinal-black transition-all hover:brightness-110 disabled:opacity-30"
      >
        {submitting ? "Enviando..." : "Enviar feedback"}
      </button>
    </div>
  );
}

"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface ListenButtonProps {
  text: string;
  estimatedMinutes?: number;
}

function stripMarkdown(text: string): string {
  return text
    .replace(/#{1,6}\s/g, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/>\s/g, "")
    .replace(/---/g, "")
    .replace(/\n{2,}/g, ". ")
    .trim();
}

export default function ListenButton({ text, estimatedMinutes }: ListenButtonProps) {
  const [mounted, setMounted] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  // Kept as ref to avoid stale closure — utterance object is not reactive state
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => {
      // Clean up speech on unmount
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handlePlay = useCallback(() => {
    if (!window.speechSynthesis) return;

    if (isPaused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
      setIsPlaying(true);
      return;
    }

    const cleanText = stripMarkdown(text);

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = "pt-BR";
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Voice selection: prefer pt-BR, fall back to any pt, then first available
    const voices = window.speechSynthesis.getVoices();
    const ptBrVoice = voices.find((v) => v.lang === "pt-BR");
    const ptVoice = voices.find((v) => v.lang.startsWith("pt"));
    utterance.voice = ptBrVoice ?? ptVoice ?? voices[0] ?? null;

    utterance.onend = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };

    utterance.onerror = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
    setIsPlaying(true);
  }, [text, isPaused]);

  const handlePause = useCallback(() => {
    window.speechSynthesis.pause();
    setIsPaused(true);
    setIsPlaying(false);
  }, []);

  const handleStop = useCallback(() => {
    window.speechSynthesis.cancel();
    setIsPlaying(false);
    setIsPaused(false);
  }, []);

  // Defer render until mounted to avoid SSR/hydration mismatch
  if (!mounted) return null;
  // Hide if Speech API is not available in this browser
  if (!window.speechSynthesis) return null;

  const minutes = estimatedMinutes ?? Math.ceil(text.split(/\s+/).filter(Boolean).length / 150);

  const statusLabel = isPlaying ? "Ouvindo..." : isPaused ? "Pausado" : "Ouvir";

  return (
    <div className="flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-2.5">
      {/* Play / Pause toggle */}
      {isPlaying ? (
        <button
          onClick={handlePause}
          className="text-signal transition-colors hover:text-signal-dim"
          aria-label="Pausar leitura"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <rect x="5" y="3" width="4" height="14" rx="1" />
            <rect x="11" y="3" width="4" height="14" rx="1" />
          </svg>
        </button>
      ) : (
        <button
          onClick={handlePlay}
          className="text-signal transition-colors hover:text-signal-dim"
          aria-label="Ouvir artigo"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M6 4l10 6-10 6V4z" />
          </svg>
        </button>
      )}

      {/* Stop button — only visible while active */}
      {(isPlaying || isPaused) && (
        <button
          onClick={handleStop}
          className="text-ash transition-colors hover:text-silver"
          aria-label="Parar leitura"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <rect x="3" y="3" width="10" height="10" rx="1" />
          </svg>
        </button>
      )}

      <span className="font-mono text-[12px] text-ash">{statusLabel}</span>
      <span className="font-mono text-[11px] text-[#4A4A56]">{minutes} min</span>

      {/* Animated bars while playing */}
      {isPlaying && (
        <div className="ml-1 flex items-end gap-[2px]" aria-hidden="true">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="w-[2px] animate-pulse rounded-full bg-signal"
              style={{ height: `${10 + i * 3}px`, animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

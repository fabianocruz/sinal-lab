"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface ListenButtonProps {
  text: string;
  estimatedMinutes?: number;
}

const SPEED_OPTIONS = [1, 1.25, 1.5, 2] as const;
type Speed = (typeof SPEED_OPTIONS)[number];

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
  const [speed, setSpeed] = useState<Speed>(1);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => {
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
    utterance.rate = speed;
    utterance.pitch = 1.0;

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
  }, [text, isPaused, speed]);

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

  const handleSpeedChange = useCallback(() => {
    const currentIdx = SPEED_OPTIONS.indexOf(speed);
    const nextIdx = (currentIdx + 1) % SPEED_OPTIONS.length;
    const newSpeed = SPEED_OPTIONS[nextIdx];
    setSpeed(newSpeed);

    // If currently playing, restart with new speed
    if (isPlaying || isPaused) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      setIsPaused(false);
      // Small delay to allow cancel to complete
      setTimeout(() => {
        const cleanText = stripMarkdown(text);
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = "pt-BR";
        utterance.rate = newSpeed;
        utterance.pitch = 1.0;

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
      }, 100);
    }
  }, [speed, isPlaying, isPaused, text]);

  if (!mounted) return null;
  if (typeof window === "undefined" || !window.speechSynthesis) return null;

  const wordCount = text.split(/\s+/).filter(Boolean).length;
  const minutes = estimatedMinutes ?? Math.ceil(wordCount / 150);
  const adjustedMinutes = Math.ceil(minutes / speed);

  return (
    <div className="flex items-center gap-3 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-2.5">
      {/* Play / Pause */}
      {isPlaying ? (
        <button
          onClick={handlePause}
          className="text-signal transition-colors hover:text-signal-dim"
          aria-label="Pausar"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <rect x="5" y="3" width="4" height="14" rx="1" />
            <rect x="11" y="3" width="4" height="14" rx="1" />
          </svg>
        </button>
      ) : (
        <button
          onClick={handlePlay}
          className="text-signal transition-colors hover:text-signal-dim"
          aria-label="Ouvir"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path d="M6 4l10 6-10 6V4z" />
          </svg>
        </button>
      )}

      {/* Stop */}
      {(isPlaying || isPaused) && (
        <button
          onClick={handleStop}
          className="text-ash transition-colors hover:text-silver"
          aria-label="Parar"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <rect x="3" y="3" width="10" height="10" rx="1" />
          </svg>
        </button>
      )}

      {/* Status + duration */}
      <span className="font-mono text-[12px] text-ash">
        {isPlaying ? "Ouvindo..." : isPaused ? "Pausado" : "Ouvir"}
      </span>
      <span className="font-mono text-[11px] text-[#4A4A56]">{adjustedMinutes} min</span>

      {/* Speed control */}
      <button
        onClick={handleSpeedChange}
        className="rounded-md border border-[rgba(255,255,255,0.08)] px-2 py-0.5 font-mono text-[11px] text-ash transition-colors hover:border-signal hover:text-signal"
        aria-label={`Velocidade: ${speed}x`}
        title="Alterar velocidade"
      >
        {speed}x
      </button>

      {/* Wave animation */}
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

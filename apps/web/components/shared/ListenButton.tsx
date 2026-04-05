"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface ListenButtonProps {
  text: string;
  estimatedMinutes?: number;
}

const SPEED_OPTIONS = [1, 1.25, 1.5, 2] as const;
type Speed = (typeof SPEED_OPTIONS)[number];

// Characters sent to ElevenLabs — matches the server-side MAX_CHARS cap.
const PREVIEW_CHARS = 5000;

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

// --- Web Speech API fallback -------------------------------------------

function speakWithWebSpeech(cleanText: string, speed: Speed, onEnd: () => void): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(cleanText.slice(0, 10000));
  utterance.lang = "pt-BR";
  utterance.rate = speed;
  const voices = window.speechSynthesis.getVoices();
  const ptVoice =
    voices.find((v) => v.lang === "pt-BR") ?? voices.find((v) => v.lang.startsWith("pt")) ?? null;
  if (ptVoice) utterance.voice = ptVoice;
  utterance.onend = onEnd;
  utterance.onerror = onEnd;
  window.speechSynthesis.speak(utterance);
}

// -----------------------------------------------------------------------

export default function ListenButton({ text, estimatedMinutes }: ListenButtonProps) {
  const [mounted, setMounted] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [speed, setSpeed] = useState<Speed>(1);

  // Cached object URL so we only call ElevenLabs once per component lifetime.
  const audioUrlRef = useRef<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Track whether we fell back to Web Speech so we manage it correctly.
  const usingFallbackRef = useRef(false);

  useEffect(() => {
    setMounted(true);
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }
      window.speechSynthesis?.cancel();
    };
  }, []);

  // Fetch audio from ElevenLabs (or return cached URL).
  const resolveAudioUrl = useCallback(async (): Promise<string | null> => {
    if (audioUrlRef.current) return audioUrlRef.current;

    setIsLoading(true);
    try {
      const cleanText = stripMarkdown(text);
      const response = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: cleanText.slice(0, PREVIEW_CHARS) }),
      });

      if (!response.ok) return null; // Caller will fall back to Web Speech

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;
      return url;
    } catch {
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [text]);

  const handlePlay = useCallback(async () => {
    // --- Resume paused ElevenLabs audio ---
    if (isPaused && audioRef.current && !usingFallbackRef.current) {
      audioRef.current.play();
      setIsPaused(false);
      setIsPlaying(true);
      return;
    }

    // --- Resume paused Web Speech ---
    if (isPaused && usingFallbackRef.current) {
      window.speechSynthesis?.resume();
      setIsPaused(false);
      setIsPlaying(true);
      return;
    }

    // --- Start fresh ---
    const url = await resolveAudioUrl();

    if (url) {
      usingFallbackRef.current = false;
      const audio = new Audio(url);
      audio.playbackRate = speed;
      audio.onended = () => {
        setIsPlaying(false);
        setIsPaused(false);
      };
      audio.onerror = () => {
        setIsPlaying(false);
        setIsPaused(false);
        // Audio element failed mid-play — fall back to Web Speech.
        usingFallbackRef.current = true;
        speakWithWebSpeech(stripMarkdown(text), speed, () => {
          setIsPlaying(false);
          setIsPaused(false);
        });
      };
      audioRef.current = audio;
      audio.play();
      setIsPlaying(true);
    } else {
      // ElevenLabs unavailable — use Web Speech.
      usingFallbackRef.current = true;
      speakWithWebSpeech(stripMarkdown(text), speed, () => {
        setIsPlaying(false);
        setIsPaused(false);
      });
      setIsPlaying(true);
    }
  }, [isPaused, resolveAudioUrl, speed, text]);

  const handlePause = useCallback(() => {
    if (usingFallbackRef.current) {
      window.speechSynthesis?.pause();
    } else {
      audioRef.current?.pause();
    }
    setIsPlaying(false);
    setIsPaused(true);
  }, []);

  const handleStop = useCallback(() => {
    if (usingFallbackRef.current) {
      window.speechSynthesis?.cancel();
    } else if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setIsPaused(false);
  }, []);

  const handleSpeedChange = useCallback(() => {
    const nextSpeed = SPEED_OPTIONS[(SPEED_OPTIONS.indexOf(speed) + 1) % SPEED_OPTIONS.length];
    setSpeed(nextSpeed);

    // Apply immediately to a live ElevenLabs audio element — no regeneration needed.
    if (audioRef.current && !usingFallbackRef.current) {
      audioRef.current.playbackRate = nextSpeed;
    }

    // Web Speech doesn't support live rate changes; restart if active.
    if (usingFallbackRef.current && (isPlaying || isPaused)) {
      window.speechSynthesis?.cancel();
      setIsPlaying(false);
      setIsPaused(false);
      // Small delay lets the browser complete the cancel before speaking again.
      setTimeout(() => {
        speakWithWebSpeech(stripMarkdown(text), nextSpeed, () => {
          setIsPlaying(false);
          setIsPaused(false);
        });
        setIsPlaying(true);
      }, 100);
    }
  }, [speed, isPlaying, isPaused, text]);

  if (!mounted) return null;

  const wordCount = text.split(/\s+/).filter(Boolean).length;
  const fullMinutes = estimatedMinutes ?? Math.ceil(wordCount / 150);
  // Preview is capped at the first ~4 min worth of the article.
  const previewMinutes = Math.min(fullMinutes, 4);
  const adjustedMinutes = Math.ceil(previewMinutes / speed);
  const isPreview = fullMinutes > 4;

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
          disabled={isLoading}
          className="text-signal transition-colors hover:text-signal-dim disabled:opacity-50"
          aria-label={isPaused ? "Continuar" : "Ouvir"}
        >
          {isLoading ? (
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              className="animate-spin"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="10" cy="10" r="7" strokeDasharray="30" strokeLinecap="round" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path d="M6 4l10 6-10 6V4z" />
            </svg>
          )}
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

      {/* Status label */}
      <span className="font-mono text-[12px] text-ash">
        {isLoading ? "Gerando..." : isPlaying ? "Ouvindo..." : isPaused ? "Pausado" : "Ouvir"}
      </span>

      {/* Duration + preview label */}
      <span className="font-mono text-[11px] text-[#4A4A56]">
        {isPreview ? `~${adjustedMinutes} min` : `${adjustedMinutes} min`}
      </span>
      {isPreview && !isPlaying && !isPaused && !isLoading && (
        <span className="font-mono text-[10px] text-[#4A4A56]">
          (primeiros {previewMinutes} min)
        </span>
      )}

      {/* Speed control */}
      <button
        onClick={handleSpeedChange}
        className="rounded-md border border-[rgba(255,255,255,0.08)] px-2 py-0.5 font-mono text-[11px] text-ash transition-colors hover:border-signal hover:text-signal"
        aria-label={`Velocidade: ${speed}x`}
        title="Alterar velocidade"
      >
        {speed}x
      </button>

      {/* Wave animation while playing */}
      {isPlaying && (
        <div className="ml-1 flex items-end gap-[2px]" aria-hidden="true">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="w-[2px] animate-pulse rounded-full bg-signal"
              style={{
                height: `${10 + i * 3}px`,
                animationDelay: `${i * 0.15}s`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { submitWaitlist } from "@/lib/api";

interface WaitlistFormProps {
  inputBg?: "graphite" | "black";
  buttonLabel?: string;
  className?: string;
}

export default function WaitlistForm({
  inputBg = "graphite",
  buttonLabel = "Assine o Briefing",
  className = "",
}: WaitlistFormProps) {
  const { status: authStatus } = useSession();
  const searchParams = useSearchParams();
  const plan = searchParams.get("plan") || undefined;
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const bgClass = inputBg === "black" ? "bg-sinal-black" : "bg-sinal-graphite";

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      setErrorMsg("Por favor, insira um email válido.");
      setStatus("error");
      return;
    }
    setStatus("loading");
    setErrorMsg("");
    try {
      await submitWaitlist({ email, plan });
      setStatus("success");
      setEmail("");
    } catch (err) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Erro ao inscrever. Tente novamente.");
    }
  }

  // Authenticated users already receive the Briefing
  if (authStatus === "authenticated") {
    return (
      <div
        className={`flex items-center gap-3 rounded-xl border border-[rgba(232,255,89,0.2)] bg-[rgba(232,255,89,0.06)] px-5 py-4 ${className}`}
      >
        <span className="text-signal">✓</span>
        <p className="font-mono text-[14px] text-signal">
          Você já recebe o Briefing!{" "}
          <Link href="/newsletter" className="underline underline-offset-2 hover:opacity-80">
            Confira as últimas edições →
          </Link>
        </p>
      </div>
    );
  }

  // Loading state — placeholder to prevent layout shift
  if (authStatus === "loading") {
    return <div className={`h-[56px] rounded-[10px] bg-[rgba(255,255,255,0.03)] ${className}`} />;
  }

  if (status === "success") {
    return (
      <div
        className={`flex items-center gap-3 rounded-xl border border-[rgba(232,255,89,0.2)] bg-[rgba(232,255,89,0.06)] px-5 py-4 ${className}`}
      >
        <span className="text-signal">✓</span>
        <p className="font-mono text-[14px] text-signal">
          Inscrição confirmada! O próximo Briefing chega na segunda-feira.
        </p>
      </div>
    );
  }

  return (
    <div className={className}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:gap-0" noValidate>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="seu@email.com"
          aria-label="Seu email"
          disabled={status === "loading"}
          className={`flex-1 border border-[rgba(255,255,255,0.06)] ${bgClass} px-5 py-4 font-body text-[15px] text-sinal-white placeholder:text-ash outline-none transition-colors focus:border-[rgba(232,255,89,0.3)] disabled:opacity-50 rounded-[10px] sm:rounded-r-none sm:border-r-0`}
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="whitespace-nowrap rounded-[10px] border border-signal bg-signal px-7 py-4 font-body text-[15px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim disabled:opacity-60 sm:rounded-l-none"
        >
          {status === "loading" ? "Inscrevendo..." : buttonLabel}
        </button>
      </form>
      {status === "error" && errorMsg && (
        <p className="mt-2 font-mono text-[12px] text-[#FF8A59]">{errorMsg}</p>
      )}
    </div>
  );
}

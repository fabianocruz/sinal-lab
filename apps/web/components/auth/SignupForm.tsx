"use client";

import React, { useState } from "react";
import Link from "next/link";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type FormStatus = "idle" | "loading" | "error";

export default function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<FormStatus>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!email || !password) {
      setErrorMsg("Preencha email e senha.");
      setStatus("error");
      return;
    }

    if (password.length < 8) {
      setErrorMsg("A senha precisa ter pelo menos 8 caracteres.");
      setStatus("error");
      return;
    }

    setStatus("loading");
    setErrorMsg("");

    // Step 1: register on the FastAPI backend.
    try {
      const registerRes = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || undefined, email, password }),
      });

      if (!registerRes.ok) {
        const body = await registerRes.json().catch(() => ({ detail: "Erro ao criar conta." }));

        // 409 = duplicate email
        if (registerRes.status === 409) {
          setErrorMsg("Este email já está em uso. Tente fazer login ou use outro email.");
        } else {
          setErrorMsg(body.detail ?? "Erro ao criar conta. Tente novamente.");
        }

        setStatus("error");
        return;
      }
    } catch {
      setErrorMsg("Erro de conexão. Verifique sua internet e tente novamente.");
      setStatus("error");
      return;
    }

    // Step 2: sign in immediately after a successful registration.
    const result = await signIn("credentials", {
      email,
      password,
      redirect: false,
    });

    if (result?.error) {
      // Registration succeeded but sign-in failed — tell the user to log in.
      setErrorMsg("Conta criada! Faça login para continuar.");
      setStatus("error");
      return;
    }

    router.push(callbackUrl);
    router.refresh();
  }

  async function handleGoogleSignIn() {
    setStatus("loading");
    setErrorMsg("");
    await signIn("google", { callbackUrl });
  }

  const isLoading = status === "loading";

  return (
    <div className="w-full max-w-[400px]">
      {/* Credentials form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="name"
            className="font-mono text-[12px] uppercase tracking-widest text-ash"
          >
            Nome (opcional)
          </label>
          <input
            id="name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Seu nome"
            disabled={isLoading}
            className="rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-3 font-body text-[15px] text-sinal-white placeholder:text-ash outline-none transition-colors focus:border-[rgba(232,255,89,0.3)] disabled:opacity-50"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="email"
            className="font-mono text-[12px] uppercase tracking-widest text-ash"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="seu@email.com"
            disabled={isLoading}
            className="rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-3 font-body text-[15px] text-sinal-white placeholder:text-ash outline-none transition-colors focus:border-[rgba(232,255,89,0.3)] disabled:opacity-50"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="password"
            className="font-mono text-[12px] uppercase tracking-widest text-ash"
          >
            Senha
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Mínimo 8 caracteres"
            disabled={isLoading}
            className="rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-3 font-body text-[15px] text-sinal-white placeholder:text-ash outline-none transition-colors focus:border-[rgba(232,255,89,0.3)] disabled:opacity-50"
          />
        </div>

        {/* Error message */}
        {status === "error" && errorMsg && (
          <p
            role="alert"
            className="rounded-lg border border-[rgba(255,138,89,0.2)] bg-[rgba(255,138,89,0.06)] px-4 py-3 font-mono text-[12px] text-[#FF8A59]"
          >
            {errorMsg}
          </p>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="mt-1 w-full rounded-lg bg-signal px-5 py-3.5 font-mono text-[14px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim disabled:opacity-60"
        >
          {isLoading ? "Criando conta..." : "Criar conta"}
        </button>
      </form>

      {/* Divider */}
      <div className="my-5 flex items-center gap-3">
        <div className="h-px flex-1 bg-[rgba(255,255,255,0.06)]" />
        <span className="font-mono text-[11px] uppercase tracking-widest text-ash">ou</span>
        <div className="h-px flex-1 bg-[rgba(255,255,255,0.06)]" />
      </div>

      {/* Google sign-in */}
      <button
        type="button"
        onClick={handleGoogleSignIn}
        disabled={isLoading}
        className="flex w-full items-center justify-center gap-3 rounded-lg border border-[rgba(255,255,255,0.1)] bg-sinal-graphite px-5 py-3.5 font-mono text-[14px] text-silver transition-colors hover:bg-sinal-slate hover:text-sinal-white disabled:opacity-60"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
          <path
            fill="#4285F4"
            d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"
          />
          <path
            fill="#34A853"
            d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"
          />
          <path
            fill="#FBBC05"
            d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"
          />
          <path
            fill="#EA4335"
            d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"
          />
        </svg>
        Entrar com Google
      </button>

      {/* Login link */}
      <p className="mt-6 text-center font-body text-[14px] text-ash">
        Já tem conta?{" "}
        <Link href="/login" className="text-signal transition-colors hover:text-signal-dim">
          Entre
        </Link>
      </p>
    </div>
  );
}

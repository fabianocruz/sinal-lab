"use client";

import React, { useState } from "react";
import { submitApiAccessRequest } from "@/lib/api";

export default function ApiAccessForm() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    role: "",
    use_case: "",
  });
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!formData.email || !formData.email.includes("@")) {
      setErrorMsg("Por favor, insira um email corporativo válido.");
      setStatus("error");
      return;
    }

    if (formData.use_case.length < 10) {
      setErrorMsg("Descreva seu caso de uso com mais detalhes (mín. 10 caracteres).");
      setStatus("error");
      return;
    }

    setStatus("loading");
    setErrorMsg("");

    try {
      await submitApiAccessRequest(formData);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Erro ao enviar. Tente novamente.");
    }
  }

  if (status === "success") {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-[rgba(232,255,89,0.2)] bg-[rgba(232,255,89,0.06)] px-5 py-4">
        <span className="text-signal">✓</span>
        <p className="font-mono text-[14px] text-signal">
          Solicitação enviada! Entraremos em contato em breve.
        </p>
      </div>
    );
  }

  const inputClass =
    "w-full border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-3 font-body text-[15px] text-sinal-white placeholder:text-ash outline-none transition-colors focus:border-[rgba(232,255,89,0.3)] disabled:opacity-50 rounded-lg";

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="api-name"
            className="mb-1.5 block font-mono text-[11px] uppercase tracking-[1.5px] text-ash"
          >
            Nome
          </label>
          <input
            id="api-name"
            name="name"
            type="text"
            required
            value={formData.name}
            onChange={handleChange}
            placeholder="Seu nome completo"
            disabled={status === "loading"}
            className={inputClass}
          />
        </div>
        <div>
          <label
            htmlFor="api-email"
            className="mb-1.5 block font-mono text-[11px] uppercase tracking-[1.5px] text-ash"
          >
            Email corporativo
          </label>
          <input
            id="api-email"
            name="email"
            type="email"
            required
            value={formData.email}
            onChange={handleChange}
            placeholder="voce@empresa.com"
            disabled={status === "loading"}
            className={inputClass}
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="api-company"
            className="mb-1.5 block font-mono text-[11px] uppercase tracking-[1.5px] text-ash"
          >
            Empresa
          </label>
          <input
            id="api-company"
            name="company"
            type="text"
            required
            value={formData.company}
            onChange={handleChange}
            placeholder="Nome da empresa"
            disabled={status === "loading"}
            className={inputClass}
          />
        </div>
        <div>
          <label
            htmlFor="api-role"
            className="mb-1.5 block font-mono text-[11px] uppercase tracking-[1.5px] text-ash"
          >
            Cargo
          </label>
          <input
            id="api-role"
            name="role"
            type="text"
            required
            value={formData.role}
            onChange={handleChange}
            placeholder="Ex: CTO, Head of Data"
            disabled={status === "loading"}
            className={inputClass}
          />
        </div>
      </div>

      <div>
        <label
          htmlFor="api-use-case"
          className="mb-1.5 block font-mono text-[11px] uppercase tracking-[1.5px] text-ash"
        >
          Caso de uso
        </label>
        <textarea
          id="api-use-case"
          name="use_case"
          required
          rows={3}
          value={formData.use_case}
          onChange={handleChange}
          placeholder="Descreva como pretende usar a API (ex: integrar dados de startups no nosso CRM...)"
          disabled={status === "loading"}
          className={`${inputClass} resize-none`}
        />
      </div>

      <button
        type="submit"
        disabled={status === "loading"}
        className="w-full rounded-lg border border-signal bg-signal px-7 py-3.5 font-body text-[15px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim disabled:opacity-60 sm:w-auto"
      >
        {status === "loading" ? "Enviando..." : "Solicitar Acesso"}
      </button>

      {status === "error" && errorMsg && (
        <p className="font-mono text-[12px] text-[#FF8A59]">{errorMsg}</p>
      )}
    </form>
  );
}

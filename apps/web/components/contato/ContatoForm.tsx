"use client";

import { useState } from "react";
import Link from "next/link";

const CONTACT_EMAIL = "contato@sinal.tech";

const TOPICS = [
  {
    id: "geral",
    label: "Dúvida geral",
    tag: "[Geral]",
    desc: "Perguntas sobre a Sinal, assinatura ou conteúdo",
    color: "#E8FF59",
  },
  {
    id: "correcao",
    label: "Reportar erro",
    tag: "[Correção]",
    desc: "Encontrou um dado incorreto? Nos ajude a corrigir",
    color: "#FF8A59",
  },
  {
    id: "parceria",
    label: "Parceria comercial",
    tag: "[Parceria]",
    desc: "Propostas de parceria, patrocínio ou integração",
    color: "#59FFB4",
  },
  {
    id: "imprensa",
    label: "Imprensa",
    tag: "[Imprensa]",
    desc: "Entrevistas, citações e informações institucionais",
    color: "#59B4FF",
  },
  {
    id: "lgpd",
    label: "Requisição LGPD",
    tag: "[LGPD]",
    desc: "Acesso, retificação, exclusão ou portabilidade dos seus dados",
    color: "#C459FF",
  },
  {
    id: "bug",
    label: "Problema técnico",
    tag: "[Bug]",
    desc: "Algo não está funcionando no site ou na newsletter",
    color: "#FF5959",
  },
] as const;

const LGPD_TYPES = [
  "Acesso aos meus dados",
  "Correção de dados",
  "Exclusão dos meus dados",
  "Portabilidade",
  "Revogação de consentimento",
  "Outra requisição",
];

type TopicId = (typeof TOPICS)[number]["id"];

export default function ContatoForm() {
  const [topic, setTopic] = useState<TopicId | "">("");
  const [lgpdType, setLgpdType] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);

  const sel = TOPICS.find((t) => t.id === topic);
  const accentColor = sel?.color || "#E8FF59";
  const isLgpd = topic === "lgpd";
  const isCorrecao = topic === "correcao";
  const canSubmit = topic && email && message && (!isLgpd || lgpdType);

  const handleSubmit = () => {
    const tag = sel?.tag || "[Geral]";
    const extra = isLgpd ? ` — ${lgpdType}` : "";
    const subject = encodeURIComponent(`${tag}${extra} ${name || "Contato via site"}`);
    const body = encodeURIComponent(
      `Assunto: ${sel?.label}${extra}\nNome: ${name || "—"}\nEmail: ${email}\n` +
        (company ? `Empresa: ${company}\n` : "") +
        (url ? `URL: ${url}\n` : "") +
        `\n---\n\n${message}`,
    );
    window.open(`mailto:${CONTACT_EMAIL}?subject=${subject}&body=${body}`, "_self");
    setSent(true);
  };

  if (sent) {
    return (
      <div className="animate-fade-up rounded-2xl border border-agent-radar/30 bg-gradient-to-br from-agent-radar/10 to-sinal-graphite p-14 text-center">
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full border-2 border-agent-radar/40 bg-agent-radar/20 text-[28px]">
          &#10003;
        </div>
        <h2 className="mb-3 font-display text-[26px] font-normal text-sinal-white">
          Mensagem preparada.
        </h2>
        <p className="mx-auto mb-7 max-w-[380px] text-sm leading-relaxed text-silver">
          Seu cliente de email abriu com a mensagem. Se não, envie para{" "}
          <strong className="text-agent-radar">{CONTACT_EMAIL}</strong>.
        </p>
        <button
          onClick={() => {
            setSent(false);
            setTopic("");
            setMessage("");
            setEmail("");
            setName("");
          }}
          className="rounded-xl border border-agent-radar/40 bg-transparent px-7 py-3 text-[13px] font-semibold text-agent-radar transition-colors hover:bg-agent-radar/10"
        >
          &#8592; Enviar outra
        </button>
      </div>
    );
  }

  return (
    <div>
      <div
        className="rounded-2xl border p-7 transition-all"
        style={{
          borderColor: `${accentColor}18`,
          background: `linear-gradient(180deg, ${accentColor}08 0%, rgba(26,26,31,0.5) 100%)`,
        }}
      >
        {/* Topic selector */}
        <div className="mb-6">
          <label className="mb-2.5 block font-mono text-[10px] uppercase tracking-[1px] text-ash">
            Assunto <span style={{ color: accentColor }}>*</span>
          </label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {TOPICS.map((t) => {
              const on = topic === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => {
                    setTopic(t.id);
                    setLgpdType("");
                  }}
                  className="rounded-xl border p-3 text-left transition-all"
                  style={{
                    borderColor: on ? `${t.color}50` : "#2A2A32",
                    background: on
                      ? `linear-gradient(135deg, ${t.color}10, ${t.color}06)`
                      : "rgba(10,10,11,0.5)",
                    boxShadow: on ? `0 2px 12px ${t.color}12` : "none",
                  }}
                >
                  <span
                    className="text-[13px] font-normal transition-colors"
                    style={{
                      color: on ? t.color : "#C4C4CC",
                      fontWeight: on ? 600 : 400,
                    }}
                  >
                    {t.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* LGPD extras */}
        {isLgpd && (
          <div className="animate-fade-up">
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[1px] text-ash">
              Tipo de requisição <span className="text-agent-mercado">*</span>
            </label>
            <select
              value={lgpdType}
              onChange={(e) => setLgpdType(e.target.value)}
              className="mb-5 w-full appearance-none rounded-xl border border-sinal-slate bg-sinal-graphite px-3.5 py-3 font-body text-sm text-sinal-white outline-none"
            >
              <option value="" disabled>
                Selecione...
              </option>
              {LGPD_TYPES.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <div className="mb-5 flex gap-2 rounded-xl border border-agent-mercado/20 bg-agent-mercado/10 p-3.5 text-xs leading-relaxed text-ash">
              <span className="text-sm text-agent-mercado">&#8505;</span>
              Requisições LGPD respondidas em até 15 dias (Art. 18, §5.º, Lei 13.709/2018).
            </div>
          </div>
        )}

        {/* Correction URL */}
        {isCorrecao && (
          <div className="animate-fade-up mb-5">
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[1px] text-ash">
              URL do conteúdo com erro
            </label>
            <input
              type="url"
              placeholder="https://sinal.tech/artigos/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full rounded-xl border border-sinal-slate bg-sinal-graphite px-3.5 py-3 font-body text-sm text-sinal-white outline-none transition-colors focus:border-agent-funding/70"
            />
          </div>
        )}

        {/* Partnership / Press company */}
        {(topic === "parceria" || topic === "imprensa") && (
          <div className="animate-fade-up mb-5">
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[1px] text-ash">
              Empresa / Veículo
            </label>
            <input
              type="text"
              placeholder="Nome da empresa"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="w-full rounded-xl border border-sinal-slate bg-sinal-graphite px-3.5 py-3 font-body text-sm text-sinal-white outline-none transition-colors focus:border-signal/70"
            />
          </div>
        )}

        {/* Name + Email */}
        <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[1px] text-ash">
              Nome
            </label>
            <input
              type="text"
              placeholder="Seu nome"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-sinal-slate bg-sinal-graphite px-3.5 py-3 font-body text-sm text-sinal-white outline-none transition-colors focus:border-signal/70"
            />
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[1px] text-ash">
              Email <span style={{ color: accentColor }}>*</span>
            </label>
            <input
              type="email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-sinal-slate bg-sinal-graphite px-3.5 py-3 font-body text-sm text-sinal-white outline-none transition-colors focus:border-signal/70"
            />
          </div>
        </div>

        {/* Message */}
        <div className="mb-6">
          <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[1px] text-ash">
            Mensagem <span style={{ color: accentColor }}>*</span>
          </label>
          <textarea
            placeholder={
              isCorrecao
                ? "Descreva o erro e indique a informação correta..."
                : isLgpd
                  ? "Descreva sua requisição..."
                  : topic === "parceria"
                    ? "Conte sobre sua proposta..."
                    : "Sua mensagem..."
            }
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={5}
            className="w-full resize-y rounded-xl border border-sinal-slate bg-sinal-black/80 px-3.5 py-3.5 font-body text-sm leading-relaxed text-sinal-white outline-none transition-colors focus:border-signal/70"
          />
        </div>

        {/* Submit */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="rounded-xl border-none px-9 py-3.5 text-sm font-bold transition-all disabled:cursor-not-allowed"
            style={{
              background: canSubmit
                ? `linear-gradient(135deg, ${accentColor}, ${accentColor}BB)`
                : "#2A2A32",
              color: canSubmit ? "#0A0A0B" : "#4A4A56",
              boxShadow: canSubmit ? `0 4px 20px ${accentColor}25` : "none",
            }}
          >
            Enviar mensagem &rarr;
          </button>
          <span className="font-mono text-[10px] text-[#4A4A56]">&#9993; {CONTACT_EMAIL}</span>
        </div>
      </div>

      <p className="mt-6 text-center text-[11px] leading-relaxed text-[#4A4A56]">
        Ao enviar, seus dados serão usados exclusivamente para responder a mensagem.{" "}
        <Link href="/privacidade" className="text-agent-mercado no-underline hover:underline">
          Política de Privacidade
        </Link>
        .
      </p>
    </div>
  );
}

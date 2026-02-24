"use client";

import { useState } from "react";

interface CopyButtonProps {
  text: string;
}

export default function CopyButton({ text }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may fail in some environments — ignore silently
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="font-mono text-[11px] text-ash transition-colors hover:text-signal"
      aria-label={copied ? "Copiado" : "Copiar codigo"}
    >
      {copied ? "Copiado!" : "Copiar"}
    </button>
  );
}

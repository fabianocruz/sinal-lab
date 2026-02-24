"use client";

import { useState } from "react";
import CopyButton from "./CopyButton";
import type { CodeExample } from "@/lib/api-docs";

const TABS = [
  { key: "curl" as const, label: "cURL" },
  { key: "python" as const, label: "Python" },
  { key: "javascript" as const, label: "JavaScript" },
];

interface CodeTabsProps {
  examples: CodeExample;
  response: string;
}

export default function CodeTabs({ examples, response }: CodeTabsProps) {
  const [active, setActive] = useState<keyof CodeExample>("curl");

  const code = examples[active];

  return (
    <div className="space-y-3">
      {/* Request */}
      <div className="rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-black">
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.04)] px-4 py-2">
          <div className="flex gap-1" role="tablist" aria-label="Linguagem do exemplo">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                role="tab"
                aria-selected={active === tab.key}
                onClick={() => setActive(tab.key)}
                className={`rounded-md px-3 py-1 font-mono text-[11px] transition-colors ${
                  active === tab.key
                    ? "bg-[rgba(232,255,89,0.06)] text-signal"
                    : "text-ash hover:text-sinal-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <CopyButton text={code} />
        </div>
        <pre className="overflow-x-auto p-4 font-mono text-[12px] leading-relaxed text-ash">
          {code}
        </pre>
      </div>

      {/* Response */}
      <div className="rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-black">
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.04)] px-4 py-2">
          <span className="font-mono text-[11px] text-ash">Resposta</span>
          <CopyButton text={response} />
        </div>
        <pre className="overflow-x-auto p-4 font-mono text-[12px] leading-relaxed text-ash">
          {response}
        </pre>
      </div>
    </div>
  );
}

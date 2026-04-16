"use client";

import { useState } from "react";
import { FAQ_ITEMS } from "./faq-data";

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  function toggle(index: number) {
    setOpenIndex(openIndex === index ? null : index);
  }

  return (
    <section id="faq" className="border-b border-[rgba(255,255,255,0.04)] py-section">
      <div className="mx-auto max-w-container px-6 md:px-10">
        {/* Section label */}
        <div className="mb-4 flex items-center gap-2.5">
          <span className="block h-px w-6 bg-signal" />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[2.5px] text-signal">
            FAQ
          </span>
        </div>

        <h2 className="mb-12 font-display text-[clamp(28px,4vw,44px)] font-normal leading-[1.15] tracking-[-0.01em] text-sinal-white">
          Perguntas frequentes.
        </h2>

        <div className="max-w-[720px]">
          {FAQ_ITEMS.map((item, index) => {
            const isOpen = openIndex === index;
            return (
              <div key={item.question} className="border-b border-[rgba(255,255,255,0.06)]">
                <button
                  onClick={() => toggle(index)}
                  className="flex w-full items-center justify-between gap-4 py-6 text-left font-body text-[16px] font-semibold text-sinal-white"
                  aria-expanded={isOpen}
                >
                  <span>{item.question}</span>
                  <span
                    className={`flex-shrink-0 font-mono text-[18px] font-light transition-transform duration-300 ${
                      isOpen ? "rotate-45 text-signal" : "text-ash"
                    }`}
                  >
                    +
                  </span>
                </button>
                <div
                  className={`overflow-hidden transition-all duration-400 ${
                    isOpen ? "max-h-[400px] pb-6" : "max-h-0"
                  }`}
                  style={{ transition: "max-height 0.4s ease, padding 0.3s" }}
                >
                  <p className="text-[15px] leading-[1.7] text-ash">{item.answer}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

"use client";

import { useEffect, useState } from "react";
import { SIDEBAR_SECTIONS } from "@/lib/api-docs";

export default function DocsSidebar() {
  const [activeId, setActiveId] = useState(SIDEBAR_SECTIONS[0].id);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { rootMargin: "-80px 0px -60% 0px", threshold: 0 },
    );

    for (const section of SIDEBAR_SECTIONS) {
      const el = document.getElementById(section.id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <>
      {/* Desktop — sticky sidebar */}
      <nav className="hidden lg:block" aria-label="Navegação da documentação">
        <div className="sticky top-[88px] space-y-1">
          {SIDEBAR_SECTIONS.map((section) => (
            <a
              key={section.id}
              href={`#${section.id}`}
              className={`block rounded-md px-3 py-1.5 font-mono text-[12px] transition-colors ${
                activeId === section.id
                  ? "bg-[rgba(232,255,89,0.06)] text-signal"
                  : "text-ash hover:text-sinal-white"
              }`}
            >
              {section.label}
            </a>
          ))}
        </div>
      </nav>

      {/* Mobile — horizontal scroll pills */}
      <nav
        className="mb-8 flex gap-2 overflow-x-auto pb-2 lg:hidden"
        aria-label="Navegação da documentação"
      >
        {SIDEBAR_SECTIONS.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            className={`whitespace-nowrap rounded-lg border px-3 py-1.5 font-mono text-[11px] transition-colors ${
              activeId === section.id
                ? "border-signal bg-[rgba(232,255,89,0.06)] text-signal"
                : "border-[rgba(255,255,255,0.06)] text-ash hover:text-sinal-white"
            }`}
          >
            {section.label}
          </a>
        ))}
      </nav>
    </>
  );
}

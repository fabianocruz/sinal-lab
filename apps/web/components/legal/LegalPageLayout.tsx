"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

interface FooterLink {
  label: string;
  href: string;
  color?: string;
}

interface LegalPageLayoutProps {
  toc: string[];
  sectionPrefix: string;
  accentColor?: string;
  footerLinks: FooterLink[];
  children: React.ReactNode;
}

export default function LegalPageLayout({
  toc,
  sectionPrefix,
  accentColor = "#E8FF59",
  footerLinks,
  children,
}: LegalPageLayoutProps) {
  const [activeSection, setActiveSection] = useState("");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) setActiveSection(e.target.id);
        });
      },
      { rootMargin: "-100px 0px -60% 0px" },
    );

    toc.forEach((_, i) => {
      const el = document.getElementById(`${sectionPrefix}${i + 1}`);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [toc, sectionPrefix]);

  return (
    <div className="mx-auto grid max-w-[1100px] grid-cols-1 gap-12 px-6 py-12 md:grid-cols-[220px_1fr] md:px-8 lg:py-12">
      {/* Sidebar TOC */}
      <aside className="hidden self-start md:sticky md:top-[100px] md:block">
        <div className="mb-3.5 font-mono text-[9px] uppercase tracking-[1.5px] text-[#4A4A56]">
          ÍNDICE
        </div>
        {toc.map((item, i) => {
          const id = `${sectionPrefix}${i + 1}`;
          const isActive = activeSection === id;
          return (
            <a
              key={i}
              href={`#${id}`}
              className="flex items-baseline gap-2 py-1.5 no-underline transition-colors"
              style={{
                borderLeft: `2px solid ${isActive ? accentColor : "transparent"}`,
                paddingLeft: "12px",
                marginLeft: "-12px",
              }}
            >
              <span className="min-w-[22px] font-mono text-[10px] text-[#4A4A56]">{i + 1}.</span>
              <span className="text-xs" style={{ color: isActive ? accentColor : "#8A8A96" }}>
                {item}
              </span>
            </a>
          );
        })}

        <div className="mt-6 border-t border-sinal-slate pt-4">
          {footerLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="mb-1.5 block text-xs no-underline transition-colors hover:text-sinal-white"
              style={{ color: link.color || "#8A8A96" }}
            >
              {link.label} &rarr;
            </Link>
          ))}
        </div>
      </aside>

      {/* Mobile TOC */}
      <nav className="rounded-lg border border-sinal-slate bg-sinal-graphite p-4 md:hidden">
        <div className="mb-2 font-mono text-[9px] uppercase tracking-[1.5px] text-[#4A4A56]">
          ÍNDICE
        </div>
        <div className="flex flex-wrap gap-2">
          {toc.map((item, i) => (
            <a
              key={i}
              href={`#${sectionPrefix}${i + 1}`}
              className="rounded-md border border-[rgba(255,255,255,0.06)] px-2.5 py-1 text-[11px] text-ash no-underline transition-colors hover:text-sinal-white"
            >
              {i + 1}. {item}
            </a>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <div>{children}</div>
    </div>
  );
}

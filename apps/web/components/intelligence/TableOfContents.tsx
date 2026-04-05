"use client";

import { useState, useEffect, useRef } from "react";

interface TocItem {
  id: string;
  text: string;
  level: number;
}

interface TableOfContentsProps {
  content: string;
}

function slugifyHeader(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // strip diacritics
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function parseHeadersFromMarkdown(markdown: string): TocItem[] {
  const lines = markdown.split("\n");
  const items: TocItem[] = [];
  const idCount: Record<string, number> = {};

  for (const line of lines) {
    const h2Match = line.match(/^##\s+(.+)$/);
    const h3Match = line.match(/^###\s+(.+)$/);

    const matched = h2Match ?? h3Match;
    const level = h2Match ? 2 : h3Match ? 3 : null;

    if (!matched || !level) continue;

    const rawText = matched[1].trim();
    const baseId = slugifyHeader(rawText);

    // Deduplicate ids
    const count = idCount[baseId] ?? 0;
    idCount[baseId] = count + 1;
    const id = count === 0 ? baseId : `${baseId}-${count}`;

    items.push({ id, text: rawText, level });
  }

  return items;
}

const MIN_SECTIONS = 3;

// ── Desktop sidebar ──────────────────────────────────────────────────────────

function DesktopToc({
  items,
  activeId,
  onLinkClick,
}: {
  items: TocItem[];
  activeId: string;
  onLinkClick: (id: string) => void;
}) {
  return (
    <nav
      aria-label="Indice do relatorio"
      className="sticky top-[100px] w-[220px] shrink-0 max-h-[calc(100vh-120px)] overflow-y-auto"
      style={{
        backgroundColor: "rgba(26,26,31,0.85)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: "8px",
        padding: "16px",
        scrollbarWidth: "none",
      }}
    >
      <p className="mb-4 font-mono text-[10px] uppercase tracking-[1.5px] text-ash">Indice</p>
      <ul className="space-y-0.5">
        {items.map((item) => {
          const isActive = activeId === item.id;
          return (
            <li key={item.id}>
              <button
                onClick={() => onLinkClick(item.id)}
                className={[
                  "w-full text-left font-mono text-[12px] leading-[1.5] transition-colors",
                  item.level === 3 ? "pl-3" : "pl-0",
                  isActive
                    ? "border-l-2 pl-[10px] text-signal"
                    : "border-l-2 border-transparent pl-[10px] text-ash hover:text-silver",
                ]
                  .join(" ")
                  .trim()}
                style={
                  isActive
                    ? { borderLeftColor: "#E8FF59", paddingTop: "4px", paddingBottom: "4px" }
                    : { borderLeftColor: "transparent", paddingTop: "4px", paddingBottom: "4px" }
                }
              >
                {item.text}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

// ── Mobile dropdown ──────────────────────────────────────────────────────────

function MobileToc({
  items,
  activeId,
  onLinkClick,
}: {
  items: TocItem[];
  activeId: string;
  onLinkClick: (id: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const h2Count = items.filter((i) => i.level === 2).length;
  const label = `Indice (${h2Count} ${h2Count === 1 ? "secao" : "secoes"})`;

  function handleClick(id: string) {
    onLinkClick(id);
    setIsOpen(false);
  }

  return (
    <div
      className="rounded-lg"
      style={{
        backgroundColor: "rgba(26,26,31,0.9)",
        border: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 font-mono text-[12px] text-ash transition-colors hover:text-silver"
        aria-expanded={isOpen}
        aria-controls="mobile-toc-list"
      >
        <span>{label}</span>
        <span
          className="transition-transform duration-200"
          style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)" }}
          aria-hidden="true"
        >
          &#8964;
        </span>
      </button>

      {isOpen && (
        <ul
          id="mobile-toc-list"
          className="border-t px-4 pb-3 pt-2 space-y-0.5"
          style={{ borderTopColor: "rgba(255,255,255,0.06)" }}
        >
          {items.map((item) => {
            const isActive = activeId === item.id;
            return (
              <li key={item.id}>
                <button
                  onClick={() => handleClick(item.id)}
                  className={[
                    "w-full text-left font-mono text-[12px] leading-[1.6] transition-colors",
                    item.level === 3 ? "pl-4" : "pl-0",
                    isActive ? "text-signal" : "text-ash hover:text-silver",
                  ].join(" ")}
                  style={{ paddingTop: "3px", paddingBottom: "3px" }}
                >
                  {item.text}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ── Main export ──────────────────────────────────────────────────────────────

export default function TableOfContents({ content }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>("");
  const observerRef = useRef<IntersectionObserver | null>(null);

  const items = parseHeadersFromMarkdown(content);

  useEffect(() => {
    if (items.length < MIN_SECTIONS) return;

    // Give MarkdownRenderer time to mount and render the headers into the DOM
    const rafId = requestAnimationFrame(() => {
      const headings = document.querySelectorAll<HTMLElement>(".prose-sinal h2, .prose-sinal h3");

      if (observerRef.current) {
        observerRef.current.disconnect();
      }

      observerRef.current = new IntersectionObserver(
        (entries) => {
          // Pick the topmost intersecting heading
          const visible = entries
            .filter((e) => e.isIntersecting)
            .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);

          if (visible.length > 0) {
            setActiveId(visible[0].target.id);
          }
        },
        {
          rootMargin: "-80px 0px -60% 0px",
          threshold: 0,
        },
      );

      headings.forEach((el) => {
        if (el.id) observerRef.current!.observe(el);
      });

      // Set initial active to first heading
      if (headings.length > 0 && headings[0].id) {
        setActiveId(headings[0].id);
      }
    });

    return () => {
      cancelAnimationFrame(rafId);
      observerRef.current?.disconnect();
    };
    // items is derived from content — content change is sufficient
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content]);

  function scrollToId(id: string) {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    setActiveId(id);
  }

  if (items.length < MIN_SECTIONS) return null;

  return (
    <>
      {/* Desktop — rendered in the sidebar slot via the parent layout */}
      <div className="hidden lg:block">
        <DesktopToc items={items} activeId={activeId} onLinkClick={scrollToId} />
      </div>

      {/* Mobile — rendered inline at top of article */}
      <div className="lg:hidden">
        <MobileToc items={items} activeId={activeId} onLinkClick={scrollToId} />
      </div>
    </>
  );
}

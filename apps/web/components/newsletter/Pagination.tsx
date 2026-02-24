"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  basePath?: string;
}

type PageItem = number | "ellipsis";

/**
 * Build a truncated page list with ellipsis for large page counts.
 * Shows first page, last page, and a window of ±1 around current page.
 * For ≤7 pages, shows all numbers without truncation.
 */
export function getPageItems(current: number, total: number): PageItem[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const items = new Set<number>();
  items.add(1);
  items.add(total);
  for (let i = current - 1; i <= current + 1; i++) {
    if (i >= 1 && i <= total) items.add(i);
  }

  const sorted = [...items].sort((a, b) => a - b);
  const result: PageItem[] = [];

  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) {
      result.push("ellipsis");
    }
    result.push(sorted[i]);
  }

  return result;
}

export default function Pagination({
  currentPage,
  totalPages,
  basePath = "/newsletter",
}: PaginationProps) {
  const searchParams = useSearchParams();
  const pageItems = getPageItems(currentPage, totalPages);

  function buildHref(page: number): string {
    const params = new URLSearchParams(searchParams.toString());
    if (page === 1) {
      params.delete("page");
    } else {
      params.set("page", String(page));
    }
    const qs = params.toString();
    return `${basePath}${qs ? `?${qs}` : ""}`;
  }

  return (
    <nav className="flex items-center justify-center gap-2 pt-12" aria-label="Paginação">
      {currentPage === 1 ? (
        <span
          className={cn(
            "h-10 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 font-mono text-[12px] tracking-[0.5px] text-ash transition-all duration-200",
            "cursor-not-allowed opacity-40",
          )}
          aria-disabled="true"
          aria-label="Página anterior"
        >
          &larr; Anterior
        </span>
      ) : (
        <Link
          href={buildHref(currentPage - 1)}
          className={cn(
            "h-10 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 font-mono text-[12px] tracking-[0.5px] text-ash transition-all duration-200",
            "hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white",
          )}
          aria-label="Página anterior"
        >
          &larr; Anterior
        </Link>
      )}

      {pageItems.map((item, idx) =>
        item === "ellipsis" ? (
          <span
            key={`ellipsis-${idx}`}
            className="flex h-10 w-10 items-center justify-center font-mono text-[13px] text-ash"
            aria-hidden="true"
          >
            &hellip;
          </span>
        ) : (
          <Link
            key={item}
            href={buildHref(item)}
            aria-current={item === currentPage ? "page" : undefined}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg border font-mono text-[13px] transition-all duration-200",
              item === currentPage
                ? "border-signal bg-signal font-semibold text-sinal-black"
                : "border-[rgba(255,255,255,0.06)] bg-sinal-graphite text-ash hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white",
            )}
          >
            {item}
          </Link>
        ),
      )}

      {currentPage === totalPages ? (
        <span
          className={cn(
            "h-10 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 font-mono text-[12px] tracking-[0.5px] text-ash transition-all duration-200",
            "cursor-not-allowed opacity-40",
          )}
          aria-disabled="true"
          aria-label="Próxima página"
        >
          Próxima &rarr;
        </span>
      ) : (
        <Link
          href={buildHref(currentPage + 1)}
          className={cn(
            "h-10 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 font-mono text-[12px] tracking-[0.5px] text-ash transition-all duration-200",
            "hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white",
          )}
          aria-label="Próxima página"
        >
          Próxima &rarr;
        </Link>
      )}
    </nav>
  );
}

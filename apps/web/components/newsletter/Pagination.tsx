import { cn } from "@/lib/utils";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
}

export default function Pagination({ currentPage, totalPages }: PaginationProps) {
  const pageNumbers = Array.from({ length: totalPages }, (_, i) => i + 1);

  return (
    <nav className="flex items-center justify-center gap-2 pt-12" aria-label="Paginação">
      <button
        disabled={currentPage === 1}
        className={cn(
          "h-10 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 font-mono text-[12px] tracking-[0.5px] text-ash transition-all duration-200",
          currentPage === 1
            ? "cursor-not-allowed opacity-40"
            : "hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white",
        )}
        aria-label="Página anterior"
      >
        &larr; Anterior
      </button>

      {pageNumbers.map((page) => (
        <button
          key={page}
          aria-current={page === currentPage ? "page" : undefined}
          className={cn(
            "h-10 w-10 rounded-lg border font-mono text-[13px] transition-all duration-200",
            page === currentPage
              ? "border-signal bg-signal font-semibold text-sinal-black"
              : "border-[rgba(255,255,255,0.06)] bg-sinal-graphite text-ash hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white",
          )}
        >
          {page}
        </button>
      ))}

      <button
        disabled={currentPage === totalPages}
        className={cn(
          "h-10 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 font-mono text-[12px] tracking-[0.5px] text-ash transition-all duration-200",
          currentPage === totalPages
            ? "cursor-not-allowed opacity-40"
            : "hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white",
        )}
        aria-label="Próxima página"
      >
        Próxima &rarr;
      </button>
    </nav>
  );
}

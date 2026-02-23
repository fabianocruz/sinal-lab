"use client";

import { useRouter, useSearchParams } from "next/navigation";

export interface FilterOption {
  value: string;
  label: string;
  color?: string;
}

interface FilterPillsProps {
  /** URL search param key to read/write (e.g. "agent" or "sector"). */
  paramKey: string;
  /** Filter options — each has a value, display label, and optional color dot. */
  options: FilterOption[];
  /** Label shown on the "show all" pill (e.g. "Todos" or "Todos os setores"). */
  allLabel: string;
  /** Base path used when building the navigation URL (e.g. "/newsletter"). */
  basePath: string;
  /** Accessible label for the wrapping role="group" element. */
  "aria-label": string;
}

/**
 * Generic filter pills component.
 *
 * Reads the active filter from the URL search param identified by `paramKey`
 * and pushes a new URL when the user selects a different pill. Selecting the
 * "all" pill removes the param entirely and resets the page to 1.
 */
export default function FilterPills({
  paramKey,
  options,
  allLabel,
  basePath,
  "aria-label": ariaLabel,
}: FilterPillsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const active = searchParams.get(paramKey) ?? "todos";

  function handleSelect(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value === "todos") {
      params.delete(paramKey);
    } else {
      params.set(paramKey, value);
    }
    // Reset to page 1 whenever the filter changes.
    params.delete("page");
    router.push(`${basePath}?${params.toString()}`);
  }

  const buttonClass = (isActive: boolean) =>
    `flex items-center gap-1.5 rounded-lg border px-4 py-2 font-mono text-[11px] uppercase tracking-[1px] transition-all duration-200 ${
      isActive
        ? "border-signal bg-[rgba(232,255,89,0.06)] text-signal"
        : "border-[rgba(255,255,255,0.06)] text-ash hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white"
    }`;

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label={ariaLabel}>
      {/* "All" pill — always first, never has a color dot */}
      <button
        onClick={() => handleSelect("todos")}
        aria-pressed={active === "todos"}
        className={buttonClass(active === "todos")}
      >
        {allLabel}
      </button>

      {options.map((option) => {
        const isActive = active === option.value;
        return (
          <button
            key={option.value}
            onClick={() => handleSelect(option.value)}
            aria-pressed={isActive}
            className={buttonClass(isActive)}
          >
            {option.color && (
              <span
                className="inline-block h-[5px] w-[5px] rounded-full"
                style={{ backgroundColor: option.color }}
                aria-hidden="true"
              />
            )}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

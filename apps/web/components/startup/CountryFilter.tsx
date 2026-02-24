"use client";

import { useRouter, useSearchParams } from "next/navigation";

const COUNTRIES = [
  { value: "todos", label: "Todos", flag: "\u{1F30E}" },
  { value: "Brasil", label: "Brasil", flag: "\u{1F1E7}\u{1F1F7}" },
  { value: "M\u00e9xico", label: "M\u00e9xico", flag: "\u{1F1F2}\u{1F1FD}" },
  { value: "Col\u00f4mbia", label: "Col\u00f4mbia", flag: "\u{1F1E8}\u{1F1F4}" },
  { value: "Argentina", label: "Argentina", flag: "\u{1F1E6}\u{1F1F7}" },
  { value: "Chile", label: "Chile", flag: "\u{1F1E8}\u{1F1F1}" },
];

export default function CountryFilter() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const active = searchParams.get("country") ?? "todos";

  function handleSelect(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value === "todos") {
      params.delete("country");
    } else {
      params.set("country", value);
    }
    params.delete("page");
    router.push(`/startups?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap gap-1" role="group" aria-label="Filtrar por pa\u00eds">
      {COUNTRIES.map((c) => {
        const isActive = active === c.value;
        return (
          <button
            key={c.value}
            onClick={() => handleSelect(c.value)}
            aria-pressed={isActive}
            className={`rounded-md border px-2.5 py-1.5 font-mono text-[11px] transition-all duration-200 ${
              isActive
                ? "border-[rgba(232,255,89,0.25)] bg-[rgba(232,255,89,0.08)] text-signal"
                : "border-sinal-slate text-ash hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white"
            }`}
          >
            <span className="mr-1">{c.flag}</span>
            {c.label}
          </button>
        );
      })}
    </div>
  );
}

"use client";

import React, { useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search } from "lucide-react";

interface SearchBarProps {
  placeholder?: string;
  basePath?: string;
}

export default function SearchBar({
  placeholder = "Buscar edições...",
  basePath = "/newsletter",
}: SearchBarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString());
      if (value.trim()) {
        params.set("q", value.trim());
      } else {
        params.delete("q");
      }
      // Reset to page 1 whenever the search query changes.
      params.delete("page");
      router.push(`${basePath}?${params.toString()}`);
    }, 300);
  }

  return (
    <div className="flex min-w-[280px] items-center gap-2 rounded-[10px] border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-3 transition-colors focus-within:border-[rgba(232,255,89,0.3)]">
      <Search size={14} className="shrink-0 text-ash" aria-hidden="true" />
      <input
        type="search"
        defaultValue={searchParams.get("q") ?? ""}
        placeholder={placeholder}
        onChange={handleChange}
        className="flex-1 bg-transparent font-body text-[14px] text-sinal-white placeholder:text-ash focus:outline-none"
        aria-label="Buscar edições"
      />
    </div>
  );
}

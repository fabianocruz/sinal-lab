'use client';

import { Search } from 'lucide-react';

interface SearchBarProps {
  placeholder?: string;
}

export default function SearchBar({ placeholder = 'Buscar edicoes...' }: SearchBarProps) {
  return (
    <div className="flex min-w-[280px] items-center gap-2 rounded-[10px] border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-4 py-3 transition-colors focus-within:border-[rgba(232,255,89,0.3)]">
      <Search size={14} className="shrink-0 text-ash" aria-hidden="true" />
      <input
        type="search"
        placeholder={placeholder}
        className="flex-1 bg-transparent font-body text-[14px] text-sinal-white placeholder:text-ash focus:outline-none"
        aria-label="Buscar edicoes"
      />
    </div>
  );
}

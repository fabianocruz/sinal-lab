'use client';

import { useState } from 'react';
import { AGENT_HEX } from '@/lib/newsletter';

interface FilterOption {
  key: string;
  label: string;
  color?: string;
}

const FILTER_OPTIONS: FilterOption[] = [
  { key: 'todos', label: 'Todos' },
  { key: 'sintese', label: 'Sintese', color: AGENT_HEX.sintese },
  { key: 'radar', label: 'Radar', color: AGENT_HEX.radar },
  { key: 'codigo', label: 'Codigo', color: AGENT_HEX.codigo },
  { key: 'funding', label: 'Funding', color: AGENT_HEX.funding },
  { key: 'mercado', label: 'Mercado', color: AGENT_HEX.mercado },
];

export default function FilterPills() {
  const [active, setActive] = useState('todos');

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por agente">
      {FILTER_OPTIONS.map((option) => {
        const isActive = active === option.key;
        return (
          <button
            key={option.key}
            onClick={() => setActive(option.key)}
            aria-pressed={isActive}
            className={`flex items-center gap-1.5 rounded-lg border px-4 py-2 font-mono text-[11px] uppercase tracking-[1px] transition-all duration-200 ${
              isActive
                ? 'border-signal bg-[rgba(232,255,89,0.06)] text-signal'
                : 'border-[rgba(255,255,255,0.06)] text-ash hover:border-[rgba(255,255,255,0.12)] hover:text-sinal-white'
            }`}
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

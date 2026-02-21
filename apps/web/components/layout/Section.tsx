import React from 'react';
import { cn } from '@/lib/utils';

interface SectionProps {
  children: React.ReactNode;
  className?: string;
  label?: string;
  id?: string;
}

export default function Section({ children, className, label, id }: SectionProps) {
  return (
    <section
      id={id}
      className={cn(
        'py-section border-b border-[rgba(255,255,255,0.04)]',
        className,
      )}
    >
      <div className="mx-auto max-w-container px-6 md:px-10">
        {label && (
          <div className="mb-6 flex items-center gap-3">
            <span className="block h-px w-6 bg-signal" />
            <span className="font-mono text-[11px] font-semibold uppercase tracking-[2px] text-signal">
              {label}
            </span>
          </div>
        )}
        {children}
      </div>
    </section>
  );
}

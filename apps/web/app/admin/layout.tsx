import React from "react";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Admin",
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="sticky top-0 flex h-screen w-56 shrink-0 flex-col border-r border-[rgba(255,255,255,0.06)] bg-sinal-graphite">
        {/* Logo */}
        <div className="flex h-14 items-center border-b border-[rgba(255,255,255,0.06)] px-5">
          <Link
            href="/admin/content"
            className="font-mono text-[13px] font-semibold tracking-[1px] text-signal"
          >
            SINAL<span className="text-ash">/admin</span>
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
          <Link
            href="/admin/content"
            className="rounded-md px-3 py-2 font-mono text-[13px] text-bone transition-colors hover:bg-[rgba(255,255,255,0.06)]"
          >
            Conteudos
          </Link>
          <Link
            href="/admin/content/new"
            className="rounded-md px-3 py-2 font-mono text-[13px] text-ash transition-colors hover:bg-[rgba(255,255,255,0.06)] hover:text-bone"
          >
            + Novo
          </Link>
        </nav>

        {/* Footer */}
        <div className="border-t border-[rgba(255,255,255,0.06)] px-5 py-3">
          <Link
            href="/"
            className="font-mono text-[11px] text-ash transition-colors hover:text-bone"
          >
            &larr; Voltar ao site
          </Link>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto bg-sinal-black px-8 py-6">{children}</main>
    </div>
  );
}

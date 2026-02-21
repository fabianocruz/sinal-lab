"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { signOut } from "next-auth/react";
import { LogOut, Settings, User } from "lucide-react";

interface UserMenuProps {
  name?: string | null;
  email?: string | null;
  isAdmin?: boolean;
}

export default function UserMenu({ name, email, isAdmin }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const initial = (name ?? email ?? "U").charAt(0).toUpperCase();

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open]);

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        aria-label="Menu da conta"
        aria-expanded={open}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-signal font-mono text-[13px] font-semibold text-sinal-black transition-opacity hover:opacity-80"
      >
        {initial}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 rounded-lg border border-[rgba(255,255,255,0.08)] bg-sinal-graphite shadow-xl">
          {/* User info */}
          <div className="border-b border-[rgba(255,255,255,0.06)] px-4 py-3">
            {name && (
              <p className="truncate font-mono text-[13px] font-semibold text-sinal-white">
                {name}
              </p>
            )}
            {email && <p className="truncate font-mono text-[12px] text-ash">{email}</p>}
          </div>

          {/* Menu items */}
          <div className="py-1">
            {isAdmin && (
              <Link
                href="/admin/content"
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-4 py-2.5 font-mono text-[13px] text-signal transition-colors hover:bg-[rgba(255,255,255,0.04)]"
              >
                <Settings size={15} />
                Admin
              </Link>
            )}
            <Link
              href="/conta"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2.5 font-mono text-[13px] text-ash transition-colors hover:bg-[rgba(255,255,255,0.04)] hover:text-sinal-white"
            >
              <User size={15} />
              Minha conta
            </Link>
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="flex w-full items-center gap-3 px-4 py-2.5 font-mono text-[13px] text-ash transition-colors hover:bg-[rgba(255,255,255,0.04)] hover:text-sinal-white"
            >
              <LogOut size={15} />
              Sair
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

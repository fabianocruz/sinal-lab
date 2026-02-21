"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { useSession } from "next-auth/react";
import UserMenu from "./UserMenu";

const NAV_LINKS = [
  { href: "/#briefing", label: "Briefing" },
  { href: "/#metodologia", label: "Metodologia" },
  { href: "/#precos", label: "Preços" },
  { href: "/#empresas", label: "Para Empresas" },
];

/**
 * Auth-aware user state: loading placeholder → "Entrar" link → UserMenu dropdown.
 */
function NavbarAuthState({ mobile = false }: { mobile?: boolean }) {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <span className="h-8 w-8" aria-hidden="true" />;
  }

  if (status === "authenticated" && session?.user) {
    return <UserMenu name={session.user.name} email={session.user.email} />;
  }

  if (mobile) {
    return (
      <Link
        href="/login"
        className="block rounded-lg px-4 py-3 font-mono text-[14px] text-ash transition-colors hover:bg-sinal-graphite hover:text-sinal-white"
      >
        Entrar
      </Link>
    );
  }

  return (
    <Link
      href="/login"
      className="font-mono text-[13px] text-ash transition-colors hover:text-sinal-white"
    >
      Entrar
    </Link>
  );
}

/**
 * Auth-aware CTA button: "Assine o Briefing" for guests, "Meu Briefing" for logged-in users.
 */
function NavbarCTA({ mobile = false, onClick }: { mobile?: boolean; onClick?: () => void }) {
  const { status } = useSession();
  const isAuth = status === "authenticated";

  const label = isAuth ? "Meu Briefing" : "Assine o Briefing";
  const href = isAuth ? "/newsletter" : "/#hero";

  if (mobile) {
    return (
      <Link
        href={href}
        onClick={onClick}
        className="mt-2 block rounded-lg bg-signal px-4 py-3 text-center font-mono text-[14px] font-semibold text-sinal-black"
      >
        {label}
      </Link>
    );
  }

  return (
    <Link
      href={href}
      className="rounded-lg bg-signal px-5 py-2.5 font-mono text-[13px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim"
    >
      {label}
    </Link>
  );
}

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 z-50 w-full transition-all duration-300 ${
        scrolled
          ? "bg-[rgba(10,10,11,0.85)] backdrop-blur-xl border-b border-[rgba(255,255,255,0.04)]"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-[72px] max-w-container items-center justify-between px-6 md:px-10">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-1.5">
          <span className="font-display text-xl text-sinal-white">Sinal</span>
          <span className="inline-block h-[6px] w-[6px] rounded-full bg-signal shadow-[0_0_12px_rgba(232,255,89,0.4)]" />
        </Link>

        {/* Desktop nav */}
        <div className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="font-mono text-[13px] text-ash transition-colors hover:text-sinal-white"
            >
              {link.label}
            </Link>
          ))}
          <Link
            href="/newsletter"
            className="font-mono text-[13px] text-ash transition-colors hover:text-sinal-white"
          >
            Arquivo
          </Link>
        </div>

        {/* Desktop: auth state + CTA */}
        <div className="hidden items-center gap-4 md:flex">
          <NavbarAuthState />
          <NavbarCTA />
        </div>

        {/* Mobile toggle */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="text-sinal-white md:hidden"
          aria-label={mobileOpen ? "Fechar menu" : "Abrir menu"}
        >
          {mobileOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="border-t border-[rgba(255,255,255,0.04)] bg-[rgba(10,10,11,0.95)] backdrop-blur-xl md:hidden">
          <div className="mx-auto max-w-container space-y-1 px-6 py-4">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="block rounded-lg px-4 py-3 font-mono text-[14px] text-ash transition-colors hover:bg-sinal-graphite hover:text-sinal-white"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/newsletter"
              onClick={() => setMobileOpen(false)}
              className="block rounded-lg px-4 py-3 font-mono text-[14px] text-ash transition-colors hover:bg-sinal-graphite hover:text-sinal-white"
            >
              Arquivo
            </Link>
            <NavbarAuthState mobile />
            <NavbarCTA mobile onClick={() => setMobileOpen(false)} />
          </div>
        </div>
      )}
    </nav>
  );
}

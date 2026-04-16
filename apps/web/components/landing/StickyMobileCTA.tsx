"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";

export default function StickyMobileCTA() {
  const [visible, setVisible] = useState(false);
  const { status } = useSession();

  useEffect(() => {
    const handleScroll = () => {
      // Show after scrolling past the hero section (~100vh)
      setVisible(window.scrollY > window.innerHeight * 0.8);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Don't show for authenticated users
  if (status === "authenticated") return null;

  return (
    <div
      className={`fixed bottom-0 left-0 z-40 w-full border-t border-[rgba(255,255,255,0.06)] bg-[rgba(10,10,11,0.95)] px-4 py-3 backdrop-blur-xl transition-transform duration-300 md:hidden ${
        visible ? "translate-y-0" : "translate-y-full"
      }`}
    >
      <Link
        href="/cadastro"
        className="block rounded-[10px] bg-signal py-3.5 text-center font-body text-[15px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim"
      >
        Receber o Briefing grátis
      </Link>
    </div>
  );
}

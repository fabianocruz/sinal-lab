import type { Metadata } from "next";
import Link from "next/link";
import AccountDetails from "@/components/auth/AccountDetails";

export const metadata: Metadata = {
  title: "Minha conta | Sinal",
  description: "Gerencie sua conta Sinal.",
};

export default function ContaPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-sinal-black px-6 py-16">
      {/* Logo */}
      <Link href="/" className="mb-10 flex items-center gap-1.5">
        <span className="font-display text-2xl text-sinal-white">Sinal</span>
        <span className="inline-block h-[7px] w-[7px] rounded-full bg-signal shadow-[0_0_12px_rgba(232,255,89,0.4)]" />
      </Link>

      {/* Card */}
      <div className="w-full max-w-[400px] rounded-2xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite p-8 shadow-[0_8px_40px_rgba(0,0,0,0.4)]">
        <div className="mb-7 text-center">
          <h1 className="font-display text-[26px] text-sinal-white">Minha conta</h1>
          <p className="mt-1.5 font-body text-[14px] text-ash">
            Gerencie seus dados e preferências.
          </p>
        </div>

        <AccountDetails />
      </div>
    </main>
  );
}

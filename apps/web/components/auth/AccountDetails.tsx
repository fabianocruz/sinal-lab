"use client";

import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { LogOut } from "lucide-react";

export default function AccountDetails() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-lg bg-[rgba(255,255,255,0.04)]" />
        ))}
      </div>
    );
  }

  if (!session?.user) return null;

  const { name, email } = session.user;
  const initial = (name ?? email ?? "U").charAt(0).toUpperCase();

  return (
    <div className="space-y-5">
      {/* Avatar + name */}
      <div className="flex items-center gap-4">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-signal font-mono text-[18px] font-bold text-sinal-black">
          {initial}
        </span>
        <div>
          {name && <p className="font-mono text-[15px] font-semibold text-sinal-white">{name}</p>}
          {email && <p className="font-mono text-[13px] text-ash">{email}</p>}
        </div>
      </div>

      {/* Info rows */}
      <div className="space-y-3 border-t border-[rgba(255,255,255,0.06)] pt-5">
        <InfoRow label="Email" value={email ?? "—"} />
        <InfoRow label="Nome" value={name ?? "Não informado"} />
        <InfoRow label="Status" value="Ativo" />
      </div>

      {/* Logout */}
      <button
        onClick={() => signOut({ callbackUrl: "/" })}
        className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-[rgba(255,255,255,0.08)] px-4 py-3 font-mono text-[13px] text-ash transition-colors hover:border-[rgba(255,255,255,0.15)] hover:text-sinal-white"
      >
        <LogOut size={15} />
        Sair da conta
      </button>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-[rgba(255,255,255,0.03)] px-4 py-3">
      <span className="font-mono text-[12px] uppercase tracking-wider text-sinal-slate">
        {label}
      </span>
      <span className="font-mono text-[13px] text-ash">{value}</span>
    </div>
  );
}

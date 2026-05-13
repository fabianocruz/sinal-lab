"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { usePathname } from "next/navigation";

interface DownloadButtonProps {
  downloadUrl: string;
  label: string;
  accentColor?: string;
}

export default function DownloadButton({
  downloadUrl,
  label,
  accentColor = "#59B4FF",
}: DownloadButtonProps) {
  const { status } = useSession();
  const isDev = process.env.NODE_ENV === "development";
  const isAuthenticated = isDev || status === "authenticated";
  const pathname = usePathname();
  const callbackParam = pathname ? `?callbackUrl=${encodeURIComponent(pathname)}` : "";

  if (isAuthenticated) {
    return (
      <a
        href={downloadUrl}
        download
        className="mt-6 inline-flex items-center gap-2 rounded-lg border px-5 py-3 font-mono text-[13px] font-semibold transition-colors"
        style={{
          borderColor: `${accentColor}33`,
          backgroundColor: `${accentColor}0F`,
          color: accentColor,
        }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M8 1v10m0 0L4.5 7.5M8 11l3.5-3.5M2 13h12"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {label}
      </a>
    );
  }

  return (
    <div className="mt-6 rounded-lg border border-[rgba(255,255,255,0.06)] bg-sinal-graphite px-5 py-4">
      <p className="text-[13px] text-silver">
        <span className="font-semibold text-bone">Download disponivel para membros.</span> Crie sua
        conta gratuita para baixar a base de dados completa.
      </p>
      <div className="mt-3 flex gap-3">
        <Link
          href={`/cadastro${callbackParam}`}
          className="rounded-lg px-4 py-2 font-mono text-[12px] font-semibold text-sinal-black transition-colors"
          style={{ backgroundColor: accentColor }}
        >
          Criar conta gratuita
        </Link>
        <Link
          href={`/login${callbackParam}`}
          className="rounded-lg border border-[rgba(255,255,255,0.06)] px-4 py-2 font-mono text-[12px] text-sinal-white transition-colors hover:bg-[rgba(255,255,255,0.04)]"
        >
          Já tenho conta
        </Link>
      </div>
    </div>
  );
}

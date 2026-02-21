import React from "react";
import { DM_Serif_Display, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import type { Metadata } from "next";
import Providers from "@/components/Providers";
import "./globals.css";

const dmSerif = DM_Serif_Display({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
  display: "swap",
});

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    template: "%s | Sinal",
    default: "Sinal — Inteligência essencial sobre o ecossistema tech LATAM",
  },
  description:
    "Toda segunda-feira, os dados mais relevantes sobre o ecossistema tech da América Latina — pesquisados por agentes de IA, revisados por humanos.",
  openGraph: {
    siteName: "Sinal",
    locale: "pt_BR",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${dmSerif.variable} ${plexSans.variable} ${plexMono.variable}`}>
      <body className="bg-sinal-black text-silver font-body antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

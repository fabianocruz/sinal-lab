import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Hero from "@/components/landing/Hero";
import SocialProof from "@/components/landing/SocialProof";
import ValueProposition from "@/components/landing/ValueProposition";
import BriefingExplainer from "@/components/landing/BriefingExplainer";
import EditionsPreviews from "@/components/landing/EditionsPreviews";
import MapaHighlight from "@/components/landing/MapaHighlight";
import IntelligenceHighlight from "@/components/landing/IntelligenceHighlight";
import HowItWorks from "@/components/landing/HowItWorks";
import Pricing from "@/components/landing/Pricing";
import Manifesto from "@/components/landing/Manifesto";
import FAQ from "@/components/landing/FAQ";
import { homepageJsonLd } from "@/lib/jsonld";

export const metadata: Metadata = {
  title: "Sinal — Inteligência essencial sobre o ecossistema tech LATAM",
  description:
    "Toda terça-feira, os dados mais relevantes sobre o ecossistema tech da América Latina — pesquisados por centenas de agentes de IA auditáveis, revisados por humanos, entregues no seu inbox.",
  openGraph: {
    title: "Sinal — Inteligência essencial sobre o ecossistema tech LATAM",
    description:
      "Toda terça-feira, os dados mais relevantes sobre o ecossistema tech da América Latina.",
    locale: "pt_BR",
    type: "website",
  },
};

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <SocialProof />
        <ValueProposition />
        <BriefingExplainer />
        <EditionsPreviews />
        <MapaHighlight />
        <IntelligenceHighlight />
        <HowItWorks />
        <Pricing />
        <Manifesto />
        <FAQ />
      </main>
      <Footer />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(homepageJsonLd()) }}
      />
    </>
  );
}

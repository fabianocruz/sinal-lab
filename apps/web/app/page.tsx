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
import StickyMobileCTA from "@/components/landing/StickyMobileCTA";
import { FAQ_ITEMS } from "@/components/landing/faq-data";
import { homepageJsonLd, faqPageJsonLd } from "@/lib/jsonld";

export const metadata: Metadata = {
  title: "Sinal: inteligência de mercado tech LATAM, grátis toda terça",
  description:
    "Briefing semanal com dados de funding, tendências e mercado do ecossistema tech da América Latina. Pesquisado por agentes de IA, verificado por humanos. 2.500+ leitores.",
  keywords:
    "LATAM tech, startup intelligence, fintech Latin America, AI startups, venture capital LATAM, Brazil tech ecosystem",
  openGraph: {
    title: "Sinal: inteligência de mercado tech LATAM, grátis toda terça",
    description:
      "Briefing semanal com dados de funding, tendências e mercado do ecossistema tech da América Latina. 2.500+ leitores.",
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
      <StickyMobileCTA />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(homepageJsonLd()) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqPageJsonLd(FAQ_ITEMS)) }}
      />
    </>
  );
}
